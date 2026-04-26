import asyncio
import os
import ssl
from datetime import datetime, timedelta

import pytz
import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests.exceptions import ChunkedEncodingError
from sqlalchemy import select, insert, delete
from sqlalchemy.orm import sessionmaker

from models import Restaurant, NoticeCategory, Notice
from scripts.menu import get_menu_data, delete_duplicate
from utils.database import get_db_engine


class HTTPSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers("AES256-GCM-SHA384")
        self.poolmanager = urllib3.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLSv1_2,
            ssl_context=ctx,
        )


async def main():
    connection = get_db_engine()
    session_constructor = sessionmaker(bind=connection)
    session = session_constructor()
    if session is None:
        raise RuntimeError("Failed to get db session")
    await execute_script(session)


async def execute_script(session):
    urls = []
    now = datetime.now()
    restaurant_query = select(Restaurant.restaurant_id)
    for restaurant_id, in session.execute(restaurant_query):
        for day_delta in range(-5, 5):
            day = now + timedelta(days=day_delta)
            urls.append((
                restaurant_id,
                f"https://www.hanyang.ac.kr/web/www/re{restaurant_id}",
                day,
            ))
    responses = []
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    with requests.Session() as request_session:
        # request_session.mount("https://", HTTPSAdapter())
        for restaurant_id, url, day in urls:
            try:
                response = request_session.get(
                    f"{url}?p_p_id=kr_ac_hanyang_cafe_web_portlet_CafePortlet&p_p_lifecycle=0&p_p_state=normal"
                    f"&p_p_mode=view"
                    f"&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_sMenuDate={day.year}%2F{day.month}%2F{day.day}"
                    f"&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_action=view",
                    verify=False,
                )
                response.raise_for_status()
                responses.append((restaurant_id, response, day))
            except ChunkedEncodingError:
                pass
    job_list = [
        get_menu_data(session, restaurant_id, response, day)
        for restaurant_id, response, day in responses
    ]
    await asyncio.gather(*job_list)
    for restaurant_id, url, day in urls:
        await delete_duplicate(session, restaurant_id, day)
    # 날씨 카테고리 검색
    notice_category_stmt = select(NoticeCategory).where(NoticeCategory.category_name == '날씨')
    notice_category = session.execute(notice_category_stmt).scalar_one_or_none()
    if notice_category is None:
        return
    # 날씨 조회 API
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    url = 'https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst'
    params = {
        'serviceKey': os.getenv('BUS_API_KEY'),
        'pageNo': '1',
        'numOfRows': '100',
        'dataType': 'JSON',
        'base_date': now.strftime('%Y%m%d'),
        'base_time': now.strftime('%H00') if now.minute > 15 else f'{now.hour - 1}00',
        'nx': '57',
        'ny': '121'
    }

    response = requests.get(url, params=params)
    result = response.json()
    items = result['response']['body']['items']['item']
    current_weather = {}
    for item in items:
        if item['category'] in ['PTY', 'T1H', 'RN1']:
            current_weather[item['category']] = item['obsrValue']
    if current_weather.get('PTY') == '0':
        weather_icon = '☀️'
    elif current_weather.get('PTY') == '2':
        weather_icon = '🌨️'
    else:
        weather_icon = '🌧️'
    korean_weather_notice = f'[날씨] {weather_icon}/현재 온도:{current_weather["T1H"]}℃'
    english_weather_notice = f'[Weather] {weather_icon}/Temp:{current_weather["T1H"]}℃'
    if (
        current_weather.get('RN1') is not None and
        str(current_weather['RN1']).isdigit() and
        int(current_weather['RN1']) > 0
    ):
        korean_weather_notice += f'/강수량:{current_weather["RN1"]}mm'
        english_weather_notice += f'/Rain:{current_weather["RN1"]}mm'
    delete_notice_stmt = delete(Notice).where(Notice.category_id == notice_category.category_id)
    insert_notice_stmt = insert(Notice).values([
        {
            'title': korean_weather_notice,
            'url': '',
            'category_id': notice_category.category_id,
            'user_id': 'admin',
            'language': 'KOREAN',
            'expired_at': now + timedelta(hours=1),
        },
        {
            'title': english_weather_notice,
            'url': '',
            'category_id': notice_category.category_id,
            'user_id': 'admin',
            'language': 'ENGLISH',
            'expired_at': now + timedelta(hours=1),
        }
    ])
    session.execute(delete_notice_stmt)
    session.execute(insert_notice_stmt)
    session.commit()
    session.close()

if __name__ == '__main__':
    asyncio.run(main())

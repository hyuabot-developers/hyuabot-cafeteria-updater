import asyncio
import ssl
from datetime import datetime, timedelta

import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests.exceptions import ChunkedEncodingError
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from models import Restaurant
from scripts.menu import get_menu_data
from utils.database import get_db_engine

from utils.database import get_master_db_engine


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
    try:
        await execute_script(session)
    except OperationalError:
        connection = get_master_db_engine()
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
    with requests.Session() as request_session:
        request_session.mount("https://", HTTPSAdapter())
        for restaurant_id, url, day in urls:
            try:
                response = request_session.get(
                    f"{url}?p_p_id=foodView_WAR_foodportlet"
                    f"&_foodView_WAR_foodportlet_sFoodDateYear={day.year}"
                    f"&_foodView_WAR_foodportlet_sFoodDateMonth={day.month - 1}"
                    f"&_foodView_WAR_foodportlet_sFoodDateDay={day.day}",
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
    session.close()

if __name__ == '__main__':
    asyncio.run(main())

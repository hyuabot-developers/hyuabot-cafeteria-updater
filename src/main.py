import asyncio
import ssl
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs, urlparse, urlunparse

import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from models import Restaurant
from scripts.menu import get_menu_data, delete_duplicate
from utils.database import get_db_engine


def build_request_url(base_url: str, day: datetime) -> str:
    parsed = urlparse(base_url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    query_params['date'] = [day.strftime("%Y-%m-%d")]
    new_query = urlencode(
        [(k, v[0]) for k, v in query_params.items()],
        doseq=False,
    )
    return urlunparse(parsed._replace(query=new_query))


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
    restaurant_query = select(Restaurant.restaurant_id, Restaurant.url)
    for restaurant_id, restaurant_url in session.execute(restaurant_query):
        if restaurant_url is None:
            continue
        for day_delta in range(-5, 5):
            day = now + timedelta(days=day_delta)
            urls.append((restaurant_id, restaurant_url, day))
    responses = []
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    with requests.Session() as request_session:
        # request_session.mount("https://", HTTPSAdapter())
        for restaurant_id, base_url, day in urls:
            try:
                request_url = build_request_url(base_url, day)
                response = request_session.get(request_url, verify=False)
                response.raise_for_status()
                responses.append((restaurant_id, response, day))
            except RequestException:
                pass
    job_list = [
        get_menu_data(session, restaurant_id, response, day)
        for restaurant_id, response, day in responses
    ]
    await asyncio.gather(*job_list)
    for restaurant_id, base_url, day in urls:
        await delete_duplicate(session, restaurant_id, day)
    session.close()

if __name__ == '__main__':
    asyncio.run(main())

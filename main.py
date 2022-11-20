import asyncio

import requests
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from models.cafeteria import Restaurant
from scripts.menu import get_menu_data
from utils.database import get_db_engine


async def main():
    connection = await get_db_engine()
    session_constructor = sessionmaker(bind=connection)
    session = session_constructor()
    if session is None:
        raise RuntimeError("Failed to get db session")
    urls = []
    restaurant_query = select([Restaurant.restaurant_id])
    for restaurant_id, in session.execute(restaurant_query):
        urls.append((restaurant_id, f"https://www.hanyang.ac.kr/web/www/re{restaurant_id}"))
    responses = [(restaurant_id, requests.get(url)) for restaurant_id, url in urls]
    job_list = [get_menu_data(session, restaurant_id, response) for restaurant_id, response in responses]
    await asyncio.gather(*job_list)
    session.close()

if __name__ == '__main__':
    asyncio.run(main())

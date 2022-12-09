import asyncio
from datetime import datetime, timedelta

import requests
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from models import Restaurant
from scripts.menu import get_menu_data
from utils.database import get_db_engine


async def main():
    connection = get_db_engine()
    session_constructor = sessionmaker(bind=connection)
    session = session_constructor()
    if session is None:
        raise RuntimeError("Failed to get db session")
    urls = []
    now = datetime.now()
    restaurant_query = select(Restaurant.restaurant_id)
    for restaurant_id, in session.execute(restaurant_query):
        for day_delta in range(-5, 5):
            day = now + timedelta(days=day_delta)
            urls.append((restaurant_id, f"https://www.hanyang.ac.kr/web/www/re{restaurant_id}", day))
    responses = [(restaurant_id, requests.get(
        f"{url}?p_p_id=foodView_WAR_foodportlet&_foodView_WAR_foodportlet_sFoodDateYear={day.year}"
        f"&_foodView_WAR_foodportlet_sFoodDateMonth={day.month - 1}&_foodView_WAR_foodportlet_sFoodDateDay={day.day}"
    ), day) for restaurant_id, url, day in urls]
    job_list = [get_menu_data(session, restaurant_id, response, day) for restaurant_id, response, day in responses]
    await asyncio.gather(*job_list)
    session.close()

if __name__ == '__main__':
    asyncio.run(main())

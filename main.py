import asyncio

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
    job_list = []
    restaurant_query = select([Restaurant.restaurant_id])
    for restaurant_id, in session.execute(restaurant_query):
        job_list.append(get_menu_data(session, restaurant_id))
    await asyncio.gather(*job_list)
    session.close()

if __name__ == '__main__':
    asyncio.run(main())

import asyncio
from datetime import datetime, timedelta, date
from typing import Optional

import pytest
import requests
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from models import BaseModel
from models import Restaurant, Menu
from scripts.menu import get_menu_data
from tests.insert_cafeteria_information import initialize_cafeteria_data
from utils.database import get_db_engine


class TestFetchRealtimeData:
    connection: Optional[Engine] = None
    session_constructor = None
    session: Optional[Session] = None

    @classmethod
    def setup_class(cls):
        cls.connection = get_db_engine()
        cls.session_constructor = sessionmaker(bind=cls.connection)
        # Database session check
        cls.session = cls.session_constructor()
        assert cls.session is not None
        # Migration schema check
        BaseModel.metadata.create_all(cls.connection)
        # Insert initial data
        asyncio.run(initialize_cafeteria_data(cls.session))
        cls.session.commit()
        cls.session.close()

    @pytest.mark.asyncio
    async def test_fetch_realtime_data(self):
        connection = get_db_engine()
        session_constructor = sessionmaker(bind=connection)
        # Database session check
        session = session_constructor()
        # Get list to fetch
        urls = []
        now = datetime.now()
        restaurant_query = select(Restaurant.restaurant_id)
        for restaurant_id, in session.execute(restaurant_query):
            for day_delta in range(-5, 5):
                day = now + timedelta(days=day_delta)
                urls.append((restaurant_id, f"https://www.hanyang.ac.kr/web/www/re{restaurant_id}", day))
        responses = [(restaurant_id, requests.get(
            f"{url}?p_p_id=foodView_WAR_foodportlet&_foodView_WAR_foodportlet_sFoodDateYear={day.year}"
            f"&_foodView_WAR_foodportlet_sFoodDateMonth={day.month - 1}"
            f"&_foodView_WAR_foodportlet_sFoodDateDay={day.day}",
        ), day) for restaurant_id, url, day in urls]
        job_list = [get_menu_data(session, restaurant_id, response, day) for restaurant_id, response, day in responses]
        await asyncio.gather(*job_list)

        # Check if the data is inserted
        menu_list = session.query(Menu).all()
        for menu_item in menu_list:  # type: Menu
            assert type(menu_item.restaurant_id) == int
            assert type(menu_item.feed_date) == date
            assert type(menu_item.time_type) == str
            assert type(menu_item.menu_food) == str
            assert type(menu_item.menu_price) == str

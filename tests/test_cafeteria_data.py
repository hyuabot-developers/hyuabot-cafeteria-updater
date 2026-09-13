import asyncio
from datetime import datetime, timedelta, date
from typing import Optional

import pytest
import requests
from requests.exceptions import RequestException
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from main import build_request_url
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
        restaurant_query = select(Restaurant.restaurant_id, Restaurant.url)
        for restaurant_id, restaurant_url in session.execute(restaurant_query):
            if restaurant_url is None:
                continue
            for day_delta in range(-5, 5):
                day = now + timedelta(days=day_delta)
                urls.append((restaurant_id, restaurant_url, day))
        responses = []
        with requests.Session() as request_session:
            for restaurant_id, base_url, day in urls:
                try:
                    request_url = build_request_url(base_url, day)
                    response = request_session.get(request_url, verify=False)
                    response.raise_for_status()
                    responses.append((restaurant_id, response, day))
                except RequestException:
                    pass
        job_list = [get_menu_data(session, restaurant_id, response, day) for restaurant_id, response, day in responses]
        await asyncio.gather(*job_list)

        # Check if the data is inserted
        menu_list = session.execute(select(Menu)).scalars().all()
        for menu_item in menu_list:  # type: Menu
            assert isinstance(menu_item.restaurant_id, int)
            assert isinstance(menu_item.feed_date, date)
            assert isinstance(menu_item.time_type, str)
            assert isinstance(menu_item.menu_food, str)
            assert isinstance(menu_item.menu_price, str)

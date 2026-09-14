import asyncio
from datetime import datetime, date
from unittest.mock import patch, MagicMock, AsyncMock

from requests.exceptions import ConnectionError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from main import build_request_url, execute_script
from models import BaseModel, Menu, Restaurant, Campus
from scripts.menu import get_menu_data


NORMAL_HTML = """
<section class="menu-section">
  <div class="menu-group">
    <div class="menu-group__title">조식</div>
    <div class="menu-list">
      <div class="menu-item">
        <div class="menu-item__name">쌀밥</div>
        <span class="menu-item__price">6,500원</span>
      </div>
      <div class="menu-item">
        <div class="menu-item__name">김치찌개</div>
        <span class="menu-item__price">6,500원</span>
      </div>
    </div>
  </div>
  <div class="menu-group">
    <div class="menu-group__title">중식</div>
    <div class="menu-list">
      <div class="menu-item">
        <div class="menu-item__name">비빔밥</div>
        <span class="menu-item__price">7,000원</span>
      </div>
    </div>
  </div>
  <div class="menu-group">
    <div class="menu-group__title">석식</div>
    <div class="menu-list">
      <div class="menu-item">
        <div class="menu-item__name">돈까스</div>
        <span class="menu-item__price">7,500원</span>
      </div>
    </div>
  </div>
</section>
"""

EMPTY_HTML = """
<section class="menu-section">
  <div class="fac-empty-msg--center">오늘의 메뉴가 없습니다.</div>
</section>
"""

NO_PRICE_HTML = """
<section class="menu-section">
  <div class="menu-group">
    <div class="menu-group__title">중식</div>
    <div class="menu-list">
      <div class="menu-item">
        <div class="menu-item__name">오늘의 스프</div>
      </div>
    </div>
  </div>
</section>
"""

MALFORMED_HTML = """
<section class="menu-section">
  <div class="menu-group">
    <div class="menu-group__title">중식</div>
    <div class="menu-list">
      <div class="menu-item">
        <div class="menu-item__name"></div>
        <span class="menu-item__price">5,000원</span>
      </div>
      <div class="menu-item">
      </div>
    </div>
  </div>
</section>
"""

DUPLICATE_HTML = """
<section class="menu-section">
  <div class="menu-group">
    <div class="menu-group__title">중식</div>
    <div class="menu-list">
      <div class="menu-item">
        <div class="menu-item__name">비빔밥</div>
        <span class="menu-item__price">7,000원</span>
      </div>
      <div class="menu-item">
        <div class="menu-item__name">비빔밥</div>
        <span class="menu-item__price">7,000원</span>
      </div>
    </div>
  </div>
</section>
"""


SIDE_DISCH_HTML = """
<section class="menu-section">
  <div class="menu-group">
    <div class="menu-group__title">중식</div>
    <div class="menu-list">
      <div class="menu-item">
        <div class="menu-item__name">장터해장국</div>
        <div class="menu-item__desc">비엔나야채볶음<br />그린샐러드</div>
        <span class="menu-item__price">6,500원</span>
      </div>
      <div class="menu-item">
        <div class="menu-item__name">나물비빔밥</div>
        <div class="menu-item__desc">춘권튀김<br />배추김치</div>
        <span class="menu-item__price">5,500원</span>
      </div>
    </div>
  </div>
</section>
"""

SIDE_DISCH_EMPTY_DESC_HTML = """
<section class="menu-section">
  <div class="menu-group">
    <div class="menu-group__title">조식</div>
    <div class="menu-list">
      <div class="menu-item">
        <div class="menu-item__name">쌀밥</div>
        <div class="menu-item__desc"></div>
        <span class="menu-item__price">5,000원</span>
      </div>
    </div>
  </div>
</section>
"""

SIDE_DISCH_NO_DESC_HTML = """
<section class="menu-section">
  <div class="menu-group">
    <div class="menu-group__title">중식</div>
    <div class="menu-list">
      <div class="menu-item">
        <div class="menu-item__name">돈까스</div>
        <span class="menu-item__price">7,000원</span>
      </div>
    </div>
  </div>
</section>
"""

SIDE_DISCH_DUPLICATE_HTML = """
<section class="menu-section">
  <div class="menu-group">
    <div class="menu-group__title">중식</div>
    <div class="menu-list">
      <div class="menu-item">
        <div class="menu-item__name">비빔밥</div>
        <div class="menu-item__desc">김치<br />김치</div>
        <span class="menu-item__price">7,000원</span>
      </div>
    </div>
  </div>
</section>
"""


class FakeResponse:
    def __init__(self, html: str):
        self.text = html


def _make_session():
    engine = create_engine("sqlite://")
    BaseModel.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _get_all_menus(db_session):
    return db_session.execute(select(Menu)).scalars().all()


class TestBuildRequestUrl:
    def test_add_date_to_url_without_query(self):
        url = build_request_url("https://example.com/menu", datetime(2026, 9, 14))
        assert url == "https://example.com/menu?date=2026-09-14"

    def test_add_date_to_url_with_other_params(self):
        url = build_request_url("https://example.com/menu?id=2", datetime(2026, 9, 14))
        assert "id=2" in url
        assert "date=2026-09-14" in url
        assert url.count("?") == 1

    def test_replace_existing_date(self):
        url = build_request_url(
            "https://example.com/menu?id=2&date=2026-09-13",
            datetime(2026, 9, 14),
        )
        assert "date=2026-09-14" in url
        assert "date=2026-09-13" not in url
        assert "id=2" in url

    def test_no_double_question_mark(self):
        url = build_request_url("https://example.com/menu?id=4", datetime(2026, 9, 14))
        assert url.count("?") == 1

    def test_preserves_scheme_and_host(self):
        url = build_request_url(
            "https://www.hanyang.ac.kr/web/www/cafeteria-menu?id=2",
            datetime(2026, 9, 15),
        )
        assert url.startswith("https://www.hanyang.ac.kr/")


class TestGetMenuData:
    def test_parse_normal_html(self):
        db_session = _make_session()
        response = FakeResponse(NORMAL_HTML)
        day = datetime(2026, 9, 14)
        asyncio.run(get_menu_data(db_session, 11, response, day))

        menus = _get_all_menus(db_session)
        assert len(menus) == 4
        db_session.close()

    def test_parse_fields_correctly(self):
        db_session = _make_session()
        response = FakeResponse(NORMAL_HTML)
        day = datetime(2026, 9, 14)
        asyncio.run(get_menu_data(db_session, 11, response, day))

        menus = _get_all_menus(db_session)
        foods = {m.menu_food for m in menus}
        assert foods == {'쌀밥', '김치찌개', '비빔밥', '돈까스'}

        time_types = {m.time_type for m in menus}
        assert time_types == {'조식', '중식', '석식'}

        for m in menus:
            assert m.restaurant_id == 11
            assert m.feed_date == date(2026, 9, 14)

        rice = next(m for m in menus if m.menu_food == '쌀밥')
        assert rice.menu_price == '6,500'
        assert rice.time_type == '조식'
        db_session.close()

    def test_empty_html_no_insert(self):
        db_session = _make_session()
        response = FakeResponse(EMPTY_HTML)
        day = datetime(2026, 9, 14)
        asyncio.run(get_menu_data(db_session, 11, response, day))

        menus = _get_all_menus(db_session)
        assert len(menus) == 0
        db_session.close()

    def test_no_price(self):
        db_session = _make_session()
        response = FakeResponse(NO_PRICE_HTML)
        day = datetime(2026, 9, 14)
        asyncio.run(get_menu_data(db_session, 11, response, day))

        menus = _get_all_menus(db_session)
        assert len(menus) == 1
        assert menus[0].menu_food == '오늘의 스프'
        assert menus[0].menu_price == ''
        db_session.close()

    def test_malformed_html_skips_empty_items(self):
        db_session = _make_session()
        response = FakeResponse(MALFORMED_HTML)
        day = datetime(2026, 9, 14)
        asyncio.run(get_menu_data(db_session, 11, response, day))

        menus = _get_all_menus(db_session)
        assert len(menus) == 0
        db_session.close()

    def test_duplicate_items_deduplicated(self):
        db_session = _make_session()
        response = FakeResponse(DUPLICATE_HTML)
        day = datetime(2026, 9, 14)
        asyncio.run(get_menu_data(db_session, 11, response, day))

        menus = _get_all_menus(db_session)
        assert len(menus) == 1
        assert menus[0].menu_food == '비빔밥'
        db_session.close()

    def test_feed_date_matches_requested_day(self):
        db_session = _make_session()
        response = FakeResponse(NORMAL_HTML)
        day = datetime(2026, 9, 15)
        asyncio.run(get_menu_data(db_session, 12, response, day))

        menus = _get_all_menus(db_session)
        for m in menus:
            assert m.feed_date == date(2026, 9, 15)
        db_session.close()

    def test_different_restaurant_ids(self):
        for rid in [11, 12, 13, 15]:
            db_session = _make_session()
            response = FakeResponse(NORMAL_HTML)
            day = datetime(2026, 9, 14)
            asyncio.run(get_menu_data(db_session, rid, response, day))

            menus = _get_all_menus(db_session)
            for m in menus:
                assert m.restaurant_id == rid
            db_session.close()

    def test_side_dishes_appended_to_menu_food(self):
        db_session = _make_session()
        response = FakeResponse(SIDE_DISCH_HTML)
        day = datetime(2026, 9, 14)
        asyncio.run(get_menu_data(db_session, 11, response, day))

        menus = _get_all_menus(db_session)
        assert len(menus) == 2
        foods = {m.menu_food for m in menus}
        assert "장터해장국, 비엔나야채볶음, 그린샐러드" in foods
        assert "나물비빔밥, 춘권튀김, 배추김치" in foods
        db_session.close()

    def test_side_dishes_empty_desc_no_suffix(self):
        db_session = _make_session()
        response = FakeResponse(SIDE_DISCH_EMPTY_DESC_HTML)
        day = datetime(2026, 9, 14)
        asyncio.run(get_menu_data(db_session, 11, response, day))

        menus = _get_all_menus(db_session)
        assert len(menus) == 1
        assert menus[0].menu_food == "쌀밥"
        db_session.close()

    def test_side_dishes_no_desc_element(self):
        db_session = _make_session()
        response = FakeResponse(SIDE_DISCH_NO_DESC_HTML)
        day = datetime(2026, 9, 14)
        asyncio.run(get_menu_data(db_session, 11, response, day))

        menus = _get_all_menus(db_session)
        assert len(menus) == 1
        assert menus[0].menu_food == "돈까스"
        db_session.close()

    def test_side_dishes_duplicate_in_desc_preserved(self):
        db_session = _make_session()
        response = FakeResponse(SIDE_DISCH_DUPLICATE_HTML)
        day = datetime(2026, 9, 14)
        asyncio.run(get_menu_data(db_session, 11, response, day))

        menus = _get_all_menus(db_session)
        assert len(menus) == 1
        assert menus[0].menu_food == "비빔밥, 김치, 김치"
        db_session.close()

    def test_replaces_existing_data_for_same_date(self):
        db_session = _make_session()
        day = datetime(2026, 9, 14)

        response1 = FakeResponse(NORMAL_HTML)
        asyncio.run(get_menu_data(db_session, 11, response1, day))
        count_before = len(_get_all_menus(db_session))

        response2 = FakeResponse(NORMAL_HTML)
        asyncio.run(get_menu_data(db_session, 11, response2, day))
        count_after = len(_get_all_menus(db_session))

        assert count_before == count_after
        db_session.close()


def _make_session_with_restaurants(restaurants):
    engine = create_engine("sqlite://")
    BaseModel.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.execute(Campus.__table__.insert(), [
        dict(campus_id=1, campus_name="서울"),
        dict(campus_id=2, campus_name="ERICA"),
    ])
    session.execute(Restaurant.__table__.insert(), restaurants)
    session.commit()
    return session


class TestExecuteScriptUrlHandling:
    def test_skips_restaurants_with_null_url(self):
        db_session = _make_session_with_restaurants([
            dict(restaurant_id=11, restaurant_name="교직원식당", campus_id=2,
                 latitude=0, longitude=0,
                 url="https://life.hanyang.ac.kr/theme/pages/facilities/detail.php?id=2"),
            dict(restaurant_id=14, restaurant_name="푸드코트", campus_id=2,
                 latitude=0, longitude=0, url=None),
        ])
        mock_response = MagicMock()
        mock_response.text = NORMAL_HTML
        mock_response.raise_for_status = MagicMock()

        with patch("main.requests.Session") as MockSession, \
             patch("main.get_menu_data", new_callable=AsyncMock) as mock_get_menu, \
             patch("main.delete_duplicate", new_callable=AsyncMock):
            mock_session_instance = MagicMock()
            mock_session_instance.get.return_value = mock_response
            mock_session_instance.__enter__ = MagicMock(return_value=mock_session_instance)
            mock_session_instance.__exit__ = MagicMock(return_value=False)
            MockSession.return_value = mock_session_instance

            asyncio.run(execute_script(db_session))

            requested_urls = [
                call.args[0] for call in mock_session_instance.get.call_args_list
            ]
            for url in requested_urls:
                assert "id=2" in url
            for call_args in mock_get_menu.call_args_list:
                assert call_args.args[1] == 11
        db_session.close()

    def test_isolates_http_errors_per_restaurant_day(self):
        db_session = _make_session_with_restaurants([
            dict(restaurant_id=11, restaurant_name="교직원식당", campus_id=2,
                 latitude=0, longitude=0,
                 url="https://life.hanyang.ac.kr/theme/pages/facilities/detail.php?id=2"),
            dict(restaurant_id=12, restaurant_name="학생식당", campus_id=2,
                 latitude=0, longitude=0,
                 url="https://life.hanyang.ac.kr/theme/pages/facilities/detail.php?id=1"),
        ])
        mock_ok_response = MagicMock()
        mock_ok_response.text = NORMAL_HTML
        mock_ok_response.raise_for_status = MagicMock()

        call_count = 0

        def side_effect(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "id=1" in url:
                raise ConnectionError("connection refused")
            return mock_ok_response

        with patch("main.requests.Session") as MockSession, \
             patch("main.get_menu_data", new_callable=AsyncMock) as mock_get_menu, \
             patch("main.delete_duplicate", new_callable=AsyncMock):
            mock_session_instance = MagicMock()
            mock_session_instance.get.side_effect = side_effect
            mock_session_instance.__enter__ = MagicMock(return_value=mock_session_instance)
            mock_session_instance.__exit__ = MagicMock(return_value=False)
            MockSession.return_value = mock_session_instance

            asyncio.run(execute_script(db_session))

            assert call_count > 0
            for call_args in mock_get_menu.call_args_list:
                assert call_args.args[1] == 11
        db_session.close()

    def test_build_request_url_with_life_hanyang_domain(self):
        url = build_request_url(
            "https://life.hanyang.ac.kr/theme/pages/facilities/detail.php?id=2",
            datetime(2026, 9, 14),
        )
        assert url.startswith("https://life.hanyang.ac.kr/")
        assert "id=2" in url
        assert "date=2026-09-14" in url
        assert url.count("?") == 1

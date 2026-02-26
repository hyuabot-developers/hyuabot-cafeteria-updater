import datetime

from bs4 import BeautifulSoup
from requests import Response
from sqlalchemy import select, delete, insert, and_
from sqlalchemy.orm import Session

from models import Menu


class HashableDict:
    """A hashable dictionary to use as a key in sets."""
    def __init__(self, data: dict):
        self._data = data
        self._frozon = frozenset(sorted(self._data.items()))

    def __hash__(self):
        return hash(self._frozon)

    def __eq__(self, other: 'HashableDict') -> bool:
        if not isinstance(other, HashableDict):
            return NotImplemented
        return (
            self._data['restaurant_id'] == other._data['restaurant_id'] and
            self._data['feed_date'] == other._data['feed_date'] and
            self._data['time_type'] == other._data['time_type'] and
            self._data['menu_food'] == other._data['menu_food']
        )

    def to_dict(self) -> dict:
        return dict(self._data)


async def get_menu_data(
        db_session: Session,
        restaurant_id: int,
        response: Response,
        day: datetime.datetime,
) -> None:
    menu_items: list[HashableDict] = []
    soup = BeautifulSoup(response.text, "html.parser")
    for daily in soup.find_all("div", class_="hyu-list-container-dailyView"):
        for inbox in daily.find_all("h3", class_="hyu-element"):
            title = inbox.get_text(strip=True)
            if not title:
                continue
            container = inbox.find_next_sibling("div", class_='hyu-list-container')
            if container:
                items = container.find_all("div", class_="hyu-list-body-item-col menu-thumbnail")
                for menu_item in items:
                    detail_p = menu_item.find_next("div", class_="menu-detail").find_next("p")
                    if not detail_p:
                        continue
                    menu_text = detail_p.get_text(strip=True)
                    price_h3 = menu_item.find_next("div", class_="menu-price").find_next("h3")
                    price_text = price_h3.get_text(strip=True) if price_h3 else ""
                    menu_item = HashableDict(dict(
                        restaurant_id=restaurant_id,
                        feed_date=day.strftime("%Y-%m-%d"),
                        time_type=title,
                        menu_food=str(menu_text).strip(),
                        menu_price=price_text,
                    ))
                    if menu_item not in menu_items:
                        menu_items.append(menu_item)
    if menu_items:
        # Remove duplicate menu items
        menu_set = [x.to_dict() for x in list(set(menu_items))]
        db_session.execute(delete(Menu).where(and_(
            Menu.restaurant_id == restaurant_id,
            Menu.feed_date == day.strftime("%Y-%m-%d"),
        )))
        insert_statement = insert(Menu).values(menu_set)
        db_session.execute(insert_statement)
    db_session.commit()


async def delete_duplicate(
    db_session: Session,
    restaurant_id: int,
    day: datetime.datetime,
) -> None:
    menu_query = select(Menu.feed_date, Menu.time_type, Menu.menu_food).where(
        Menu.restaurant_id == restaurant_id,
        Menu.feed_date == day.strftime("%Y-%m-%d"),
    )
    menu_items = {}
    for feed_date, time_type, menu_food in db_session.execute(menu_query):
        if menu_food not in menu_items:
            menu_items[menu_food] = [time_type]
        else:
            menu_items[menu_food].append(time_type)
    deleted_items = 0
    for menu_food, time_types in menu_items.items():
        if len(time_types) == 1:
            continue
        elif "석식" in time_types:
            db_session.execute(delete(Menu).where(and_(
                Menu.restaurant_id == restaurant_id,
                Menu.feed_date == day.strftime("%Y-%m-%d"),
                Menu.time_type != "석식",
                Menu.menu_food == menu_food,
            )))
            deleted_items += 1
        elif "중식" in time_types:
            db_session.execute(delete(Menu).where(and_(
                Menu.restaurant_id == restaurant_id,
                Menu.feed_date == day.strftime("%Y-%m-%d"),
                Menu.time_type != "중식",
                Menu.menu_food == menu_food,
            )))
            deleted_items += 1
    print(f"deleted {deleted_items} items")

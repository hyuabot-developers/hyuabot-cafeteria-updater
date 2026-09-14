import datetime

from bs4 import BeautifulSoup, Tag
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

    def __eq__(self, other: object) -> bool:
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
    for section in soup.find_all("section", class_="menu-section"):
        for group in section.find_all("div", class_="menu-group"):
            title_el = group.find("div", class_="menu-group__title")
            if not title_el:
                continue
            time_type = title_el.get_text(strip=True)
            if not time_type:
                continue
            menu_list = group.find("div", class_="menu-list")
            if not menu_list:
                continue
            for item in menu_list.find_all("div", class_="menu-item"):
                if not isinstance(item, Tag):
                    continue
                name_el = item.find("div", class_="menu-item__name")
                if not name_el:
                    continue
                menu_food = name_el.get_text(strip=True)
                if not menu_food:
                    continue
                desc_el = item.find("div", class_="menu-item__desc")
                if desc_el:
                    side_dishes = [
                        t.strip()
                        for t in desc_el.get_text(separator="\n").split("\n")
                        if t.strip()
                    ]
                    if side_dishes:
                        menu_food = menu_food + ", " + ", ".join(side_dishes)
                price_el = item.find("span", class_="menu-item__price")
                price_text = price_el.get_text(strip=True) if price_el else ""
                price_text = price_text.replace("원", "").strip()
                menu_entry = HashableDict(dict(
                    restaurant_id=restaurant_id,
                    feed_date=day.date(),
                    time_type=time_type,
                    menu_food=menu_food,
                    menu_price=price_text,
                ))
                if menu_entry not in menu_items:
                    menu_items.append(menu_entry)
    if menu_items:
        menu_set = [x.to_dict() for x in list(set(menu_items))]
        db_session.execute(delete(Menu).where(and_(
            Menu.restaurant_id == restaurant_id,
            Menu.feed_date == day.date(),
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
        Menu.feed_date == day.date(),
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
                Menu.feed_date == day.date(),
                Menu.time_type != "석식",
                Menu.menu_food == menu_food,
            )))
            deleted_items += 1
        elif "중식" in time_types:
            db_session.execute(delete(Menu).where(and_(
                Menu.restaurant_id == restaurant_id,
                Menu.feed_date == day.date(),
                Menu.time_type != "중식",
                Menu.menu_food == menu_food,
            )))
            deleted_items += 1
    print(f"deleted {deleted_items} items")

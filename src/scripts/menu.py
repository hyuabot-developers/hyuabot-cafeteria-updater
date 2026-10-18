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


WEEKLY_TABLE_CLASS = "weekly-table"


def _header_date(header: Tag, reference: datetime.date) -> datetime.date | None:
    """Turn a weekly-table day header such as '10.18' into a full date near the reference."""
    date_el = header.find("span", class_="th-day-date")
    if date_el is None:
        return None
    try:
        month_text, day_text = date_el.get_text(strip=True).split(".")
        candidate = datetime.date(reference.year, int(month_text), int(day_text))
    except ValueError:
        return None
    # The header has no year, so pick the one that places the date closest to the reference.
    delta_days = (candidate - reference).days
    if delta_days > 180:
        candidate = candidate.replace(year=candidate.year - 1)
    elif delta_days < -180:
        candidate = candidate.replace(year=candidate.year + 1)
    return candidate


def _find_day_column(table: Tag, target: datetime.date) -> int | None:
    for index, header in enumerate(table.find_all("th", class_="th-day")):
        if _header_date(header, target) == target:
            return index
    return None


def _parse_weekly_item(
        item: Tag,
        restaurant_id: int,
        day: datetime.datetime,
        time_type: str,
) -> HashableDict | None:
    name_el = item.find("div", class_="weekly-item-name")
    if name_el is None:
        return None
    menu_food = name_el.get_text(strip=True)
    if not menu_food:
        return None
    desc_el = item.find("div", class_="weekly-item-desc")
    if desc_el is not None:
        side_dishes = [
            side.strip()
            for side in desc_el.get_text().split("/")
            if side.strip()
        ]
        if side_dishes:
            menu_food = ", ".join([menu_food, *side_dishes])
    price_el = item.find("div", class_="weekly-item-price")
    price_text = price_el.get_text(strip=True).replace("원", "").strip() if price_el else ""
    return HashableDict(dict(
        restaurant_id=restaurant_id,
        feed_date=day.date(),
        time_type=time_type,
        menu_food=menu_food,
        menu_price=price_text,
    ))


async def get_menu_data(
        db_session: Session,
        restaurant_id: int,
        response: Response,
        day: datetime.datetime,
) -> None:
    menu_items: list[HashableDict] = []
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_=WEEKLY_TABLE_CLASS)
    column = _find_day_column(table, day.date()) if isinstance(table, Tag) else None
    if isinstance(table, Tag) and column is not None:
        # The page shows a whole week; only the column for the requested day is stored.
        for row in table.find_all("tr"):
            label_el = row.find("th", class_="td-meal-label")
            if label_el is None:
                continue
            time_type = label_el.get_text(strip=True)
            if not time_type:
                continue
            cells = row.find_all("td", class_="td-menu-cell")
            if column >= len(cells):
                continue
            for item in cells[column].find_all("div", class_="weekly-text-item"):
                menu_entry = _parse_weekly_item(item, restaurant_id, day, time_type)
                if menu_entry is not None and menu_entry not in menu_items:
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

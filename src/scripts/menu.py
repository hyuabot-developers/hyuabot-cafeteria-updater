import datetime

from bs4 import BeautifulSoup
from requests import Response
from sqlalchemy import delete, insert, and_
from sqlalchemy.orm import Session

from models import Menu


async def get_menu_data(
        db_session: Session,
        restaurant_id: int,
        response: Response,
        day: datetime.datetime,
) -> None:
    menu_items: list[dict] = []
    soup = BeautifulSoup(response.text, "html.parser")
    for inbox in soup.find_all("div", {"class": "in-box"}):
        title = inbox.find("h4").text.strip()
        for list_item in inbox.find_all("li"):
            if list_item.find("h3"):
                menu = list_item.find("h3").text.replace("\t", "").replace("\r\n", "")
                p = list_item.find("p", {"class": "price"}).text
                menu_item = dict(
                    restaurant_id=restaurant_id,
                    feed_date=day.strftime("%Y-%m-%d"),
                    time_type=title,
                    menu_food=str(menu).strip(),
                    menu_price=p,
                )
                if menu_item not in menu_items:
                    menu_items.append(menu_item)
    db_session.execute(delete(Menu).where(and_(
        Menu.restaurant_id == restaurant_id,
        Menu.feed_date == day.strftime("%Y-%m-%d"),
    )))
    if menu_items:
        insert_statement = insert(Menu).values(menu_items)
        db_session.execute(insert_statement)
    db_session.commit()

from aiohttp import ClientTimeout, ClientSession
from bs4 import BeautifulSoup
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from models.cafeteria import Menu


async def get_menu_data(db_session: Session, restaurant_id: int) -> None:
    url = f"https://www.hanyang.ac.kr/web/www/re{restaurant_id}"
    timeout = ClientTimeout(total=3.0)
    menu_items: list[dict] = []
    async with ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
            for inbox in soup.find_all("div", {"class": "in-box"}):
                title = inbox.find("h4").text.strip()
                for list_item in inbox.find_all("li"):
                    if list_item.find("h3"):
                        menu = list_item.find("h3").text.replace("\t", "").replace("\r\n", "")
                        p = list_item.find("p", {"class": "price"}).text
                        menu_items.append(dict(
                            restaurant_id=restaurant_id,
                            time_type=title,
                            menu=menu,
                            menu_price=p,
                        ))
    db_session.execute(delete(Menu).where(Menu.restaurant_id == restaurant_id))
    if menu_items:
        insert_statement = insert(Menu).values(menu_items)
        db_session.execute(insert_statement)
    db_session.commit()

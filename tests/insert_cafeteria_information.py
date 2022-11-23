from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models import Restaurant
from models import Campus


async def initialize_cafeteria_data(db_session: Session):
    await insert_campus_data(db_session)
    await insert_cafeteria_data(db_session)


async def insert_campus_data(db_session: Session):
    insert_statement = insert(Campus).values([
        dict(campus_id=1, campus_name="서울"), dict(campus_id=2, campus_name="ERICA"),
    ])
    insert_statement = insert_statement.on_conflict_do_update(
        index_elements=["campus_id"],
        set_=dict(campus_name=insert_statement.excluded.campus_name),
    )
    db_session.execute(insert_statement)
    db_session.commit()


async def insert_cafeteria_data(db_session: Session):
    supported_restaurants = [
        dict(restaurant_id=1, restaurant_name="학생식당", campus_id=1, latitude=0, longitude=0),
        dict(restaurant_id=2, restaurant_name="생활과학관식당", campus_id=1, latitude=0, longitude=0),
        dict(restaurant_id=4, restaurant_name="신소재공학관 식당", campus_id=1, latitude=0, longitude=0),
        dict(restaurant_id=5, restaurant_name="제1생활관 식당", campus_id=1, latitude=0, longitude=0),
        dict(restaurant_id=7, restaurant_name="제2생활관 식당", campus_id=1, latitude=0, longitude=0),
        dict(restaurant_id=8, restaurant_name="행원파크", campus_id=1, latitude=0, longitude=0),
        dict(restaurant_id=11, restaurant_name="교직원식당", campus_id=2, latitude=0, longitude=0),
        dict(restaurant_id=12, restaurant_name="학생식당", campus_id=2, latitude=0, longitude=0),
        dict(restaurant_id=13, restaurant_name="창의인재원식당", campus_id=2, latitude=0, longitude=0),
        dict(restaurant_id=14, restaurant_name="푸드코트", campus_id=2, latitude=0, longitude=0),
        dict(restaurant_id=15, restaurant_name="창업보육센터", campus_id=2, latitude=0, longitude=0),
    ]
    insert_statement = insert(Restaurant).values(supported_restaurants)
    insert_statement = insert_statement.on_conflict_do_update(
        index_elements=["restaurant_id"],
        set_=dict(
            restaurant_name=insert_statement.excluded.restaurant_name,
            campus_id=insert_statement.excluded.campus_id,
            latitude=insert_statement.excluded.latitude,
            longitude=insert_statement.excluded.longitude,
        ),
    )
    db_session.execute(insert_statement)
    db_session.commit()

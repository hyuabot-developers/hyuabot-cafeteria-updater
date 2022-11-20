from sqlalchemy import PrimaryKeyConstraint, Column
from sqlalchemy.sql import sqltypes

from models import BaseModel


class Restaurant(BaseModel):
    __tablename__ = 'restaurant'
    campus_id = Column(sqltypes.Integer, nullable=False)
    restaurant_id = Column(sqltypes.Integer, primary_key=True)
    restaurant_name = Column(sqltypes.String(50), nullable=False)
    latitude = Column(sqltypes.Float, nullable=False)
    longitude = Column(sqltypes.Float, nullable=False)


class Menu(BaseModel):
    __tablename__ = 'menu'
    __table_args__ = (
        PrimaryKeyConstraint('restaurant_id', 'menu'),
    )
    restaurant_id = Column(sqltypes.Integer, nullable=False)
    time_type = Column(sqltypes.String(10), nullable=False)
    menu = Column(sqltypes.String(100), nullable=False)
    menu_price = Column(sqltypes.String(20), nullable=False)

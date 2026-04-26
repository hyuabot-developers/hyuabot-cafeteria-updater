import datetime

from sqlalchemy import ForeignKey, String, Double, PrimaryKeyConstraint, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class BaseModel(DeclarativeBase):
    pass


class Campus(BaseModel):
    __tablename__ = "campus"
    campus_id: Mapped[int] = mapped_column(primary_key=True)
    campus_name: Mapped[str] = mapped_column(nullable=False)


class Restaurant(BaseModel):
    __tablename__ = 'restaurant'
    campus_id: Mapped[int] = mapped_column(ForeignKey('campus.campus_id'), nullable=False)
    restaurant_id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_name: Mapped[str] = mapped_column(String(50), nullable=False)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)


class Menu(BaseModel):
    __tablename__ = 'menu'
    __table_args__ = (
        PrimaryKeyConstraint('restaurant_id', 'feed_date', 'time_type', 'menu_food'),
    )
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurant.restaurant_id'), nullable=False)
    feed_date: Mapped[datetime.date] = mapped_column(nullable=False)
    time_type: Mapped[str] = mapped_column(String(10), nullable=False)
    menu_food: Mapped[str] = mapped_column(String(400), nullable=False)
    menu_price: Mapped[str] = mapped_column(String(30), nullable=False)


class NoticeCategory(BaseModel):
    __tablename__ = 'notice_category'
    category_id: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=True)
    category_name: Mapped[str] = mapped_column(String(20), nullable=False)


class Notice(BaseModel):
    __tablename__ = 'notices'
    notice_id: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(200), nullable=False)
    expired_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('notice_category.category_id'), nullable=False)
    user_id: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)

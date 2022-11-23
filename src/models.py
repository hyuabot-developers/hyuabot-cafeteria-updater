from sqlalchemy import ForeignKey, String, Double, PrimaryKeyConstraint
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
        PrimaryKeyConstraint('restaurant_id', 'menu'),
    )
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurant.restaurant_id'), nullable=False)
    time_type: Mapped[str] = mapped_column(String(10), nullable=False)
    menu: Mapped[str] = mapped_column(String(100), nullable=False)
    menu_price: Mapped[str] = mapped_column(String(20), nullable=False)

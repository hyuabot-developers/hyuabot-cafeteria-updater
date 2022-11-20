from sqlalchemy import Column
from sqlalchemy.sql import sqltypes

from models import BaseModel


class Campus(BaseModel):
    __tablename__ = "campus"
    campus_id = Column(sqltypes.Integer, primary_key=True)
    campus_name = Column(sqltypes.String, nullable=False)

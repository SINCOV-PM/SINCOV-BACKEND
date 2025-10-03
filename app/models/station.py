from sqlalchemy import Column, BigInteger, String, Float
from app.db.base_class import Base

class Station(Base):
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    description = Column(String, nullable=True)
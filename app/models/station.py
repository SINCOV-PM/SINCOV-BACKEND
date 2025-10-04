from sqlalchemy import Column, BigInteger, String, Float, Integer
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Station(Base):
    __tablename__ = "stations"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    station_rmcab_id = Column(Integer, unique=True, index=True, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    reports = relationship("Report", back_populates="station", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="station", cascade="all, delete-orphan")
    monitors = relationship("Monitor", back_populates="station", cascade="all, delete-orphan")


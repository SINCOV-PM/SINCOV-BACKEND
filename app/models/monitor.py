from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    station_id = Column(BigInteger, ForeignKey("stations.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)   # E.g.: "PM2.5", "Temperature", "Humidity"
    code = Column(String(100), nullable=True)  # E.g.: "S_##_##"
    unit = Column(String(20), nullable=True)    # E.g.: "µg/m3", "°C", "%"

    station = relationship("Station", back_populates="monitors")
    sensors = relationship("Sensor", back_populates="monitor", cascade="all, delete-orphan")

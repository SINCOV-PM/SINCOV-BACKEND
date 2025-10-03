from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    station_id = Column(BigInteger, ForeignKey("stations.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)   # Ej: "PM2.5", "Temperature", "Humidity"
    model = Column(String(100), nullable=True) # Ej: "AQMesh V5", "Custom IoT Node"
    unit = Column(String(20), nullable=True)   # Ej: "µg/m3", "°C", "%"

    station = relationship("Station", back_populates="monitors")
    sensors = relationship("Sensor", back_populates="monitor", cascade="all, delete-orphan")

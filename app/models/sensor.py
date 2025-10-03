from sqlalchemy import Column, BigInteger, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    monitor_id = Column(BigInteger, ForeignKey("monitors.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    value = Column(Float, nullable=False)

    monitor = relationship("Monitor", back_populates="sensors")

from sqlalchemy import Column, BigInteger, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    station_id = Column(BigInteger, ForeignKey("stations.id"), nullable=True, index=True)
    features = Column(JSON, nullable=False)  # almacena la lista de features como JSON
    result = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    station = relationship("Station", back_populates="predictions")

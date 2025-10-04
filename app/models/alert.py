from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base_class import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    prediction_id = Column(BigInteger, ForeignKey("predictions.id"), nullable=False)
    message = Column(String(255), nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subscription = relationship("Subscription", back_populates="alerts")
    prediction = relationship("Prediction", back_populates="alerts")

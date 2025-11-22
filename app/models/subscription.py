from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base_class import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    is_subscribed = Column(Boolean, default=True, nullable=False)
    station_preference_type = Column(String(20), default="all", nullable=False) # 'all', 'specific', 'none'
    station_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc),)

    alerts = relationship("Alert", back_populates="subscription", cascade="all, delete-orphan")

from sqlalchemy import Column, Integer, String, Boolean
from app.db.base_class import Base

class Subscription(Base):
    __tablename__ = "subscription"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    is_subscribed = Column(Boolean, default=True)

from sqlalchemy import Column, BigInteger, Date, Float, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    station_id = Column(BigInteger, ForeignKey("stations.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    avg = Column(Float, nullable=False)
    status = Column(String(50), nullable=False)

    station = relationship("Station", back_populates="reports")

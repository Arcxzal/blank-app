# backend/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .database import Base


class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    sensor = Column(Integer, index=True)
    mux = Column(Integer, nullable=True)
    channel = Column(Integer, nullable=True)
    voltage = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

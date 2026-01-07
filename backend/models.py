# backend/models.py
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from .database import Base

class PressureSample(Base):
    __tablename__ = "pressure_samples"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    timestamp = Column(DateTime)
    big_toe = Column(Float)
    pinky_toe = Column(Float)
    meta_out = Column(Float)
    meta_in = Column(Float)
    heel = Column(Float)
    mux = Column(Integer, nullable=True)

# backend/models.py
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationship to pressure samples
    pressure_samples = relationship("PressureSample", back_populates="patient")

class PressureSample(Base):
    __tablename__ = "pressure_samples"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True, index=True)  # nullable for backward compatibility
    device_id = Column(String, index=True)
    timestamp = Column(DateTime)
    # Right foot sensors
    big_toe = Column(Float)
    pinky_toe = Column(Float)
    meta_out = Column(Float)
    meta_in = Column(Float)
    heel = Column(Float)
    # Left foot sensors
    big_toe_l = Column(Float, nullable=True)
    pinky_toe_l = Column(Float, nullable=True)
    meta_out_l = Column(Float, nullable=True)
    meta_in_l = Column(Float, nullable=True)
    heel_l = Column(Float, nullable=True)
    mux = Column(Integer, nullable=True)
    
    # Relationship to patient
    patient = relationship("Patient", back_populates="pressure_samples")

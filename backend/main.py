from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from sqlalchemy import Column, Integer, Float, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI(title="ESP32 Sensor API")
Base = declarative_base()

# SQLite database setup
DATABASE_URL = "sqlite:///./sensor_data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# SQLAlchemy model for sensor data
class SensorDataDB(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    temperature = Column(Float)
    humidity = Column(Float)

# Pydantic model for requests
class SensorData(BaseModel):
    device_id: str
    temperature: float
    humidity: float

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "FastAPI backend is running"}

# POST sensor data
@app.post("/sensor-data/")
def receive_data(sensor: SensorData):
    db = SessionLocal()
    db_data = SensorDataDB(
        device_id=sensor.device_id,
        temperature=sensor.temperature,
        humidity=sensor.humidity
    )
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    db.close()
    return {"status": "success", "received": sensor.dict()}

# GET all sensor data
@app.get("/sensor-data/")
def get_data():
    db = SessionLocal()
    all_data = db.query(SensorDataDB).all()
    db.close()
    return [
        {"device_id": d.device_id, "temperature": d.temperature, "humidity": d.humidity}
        for d in all_data
    ]

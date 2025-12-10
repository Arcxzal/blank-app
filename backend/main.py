# backend/main.py
import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas
from .database import SessionLocal, engine

# Create DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ESP32 Pressure Receiver")

# Allow CORS for Streamlit or web dashboards
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency: get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/pressure", status_code=201)
async def receive(payload: schemas.Payload, db: Session = Depends(get_db)):
    if not payload.readings:
        raise HTTPException(status_code=400, detail="No readings included")

    rows = []
    for r in payload.readings:
        obj = models.Reading(
            device_id=payload.device_id,
            sensor=r.sensor,
            mux=r.mux,
            channel=r.channel,
            voltage=r.voltage,
        )
        db.add(obj)
        rows.append(obj)

    db.commit()
    for obj in rows:
        db.refresh(obj)

    return {"status": "ok", "inserted": len(rows)}


@app.get("/api/readings", response_model=List[schemas.ReadingOut])
def get_readings(limit: int = 500, device_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Reading).order_by(models.Reading.created_at.desc())
    if device_id:
        q = q.filter(models.Reading.device_id == device_id)
    q = q.limit(limit)
    results = list(q)
    results.reverse()  # chronological order
    return results


@app.get("/api/summary")
def summary(db: Session = Depends(get_db)):
    from sqlalchemy import func
    total = db.query(func.count(models.Reading.id)).scalar()
    last = db.query(func.max(models.Reading.created_at)).scalar()
    return {"total_readings": total, "last": last}

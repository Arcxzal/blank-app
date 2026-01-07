# backend/main.py
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from . import models, schemas
from .database import SessionLocal, engine
from typing import List

# Create DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ESP32 Pressure API")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/pressure", status_code=201)
async def receive(payload: schemas.Payload, db: Session = Depends(get_db)):
    # Accept multiple payload shapes. Use `get_readings()` to normalize.
    readings = []
    try:
        readings = payload.get_readings()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload format")

    if not readings:
        raise HTTPException(status_code=400, detail="Payload contains no readings")

    rows = []
    for r in readings:
        row = models.PressureSample(
            device_id=payload.device_id,
            timestamp=r.timestamp,
            big_toe=r.bigToe,
            pinky_toe=r.pinkyToe,
            meta_out=r.metaOut,
            meta_in=r.metaIn,
            heel=r.heel,
        )
        db.add(row)
        rows.append(row)

    db.commit()
    for row in rows:
        db.refresh(row)

    return {"status": "ok", "inserted": len(rows)}

@app.get("/api/readings", response_model=List[schemas.Sample])
def get_readings(limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(models.PressureSample).order_by(models.PressureSample.timestamp.desc()).limit(limit)
    results = list(q)
    results.reverse()  # chronological order

    # Convert DB rows to API schema
    response = []
    for r in results:
        response.append(
            schemas.Sample(
                timestamp=r.timestamp,
                pressures=schemas.PressureSet(
                    bigToe=r.big_toe,
                    pinkyToe=r.pinky_toe,
                    metaOut=r.meta_out,
                    metaIn=r.meta_in,
                    heel=r.heel
                ),
                mux=r.mux
            )
        )
    return response


@app.get("/api/readings/compact", response_model=List[schemas.SimpleReading])
def get_readings_compact(limit: int = 50, db: Session = Depends(get_db)):
    """Return the last `limit` readings in compact format: timestamp (int) and s1..s5."""
    q = db.query(models.PressureSample).order_by(models.PressureSample.timestamp.desc()).limit(limit)
    results = list(q)
    results.reverse()

    response = []
    for r in results:
        # timestamp as integer seconds since epoch
        ts = int(r.timestamp.timestamp()) if r.timestamp is not None else 0
        response.append(
            schemas.SimpleReading(
                timestamp=ts,
                s1=r.big_toe,
                s2=r.pinky_toe,
                s3=r.meta_out,
                s4=r.meta_in,
                s5=r.heel,
            )
        )
    return response

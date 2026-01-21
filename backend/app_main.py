# backend/main.py
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from . import models, schemas
from .database import SessionLocal, engine
from typing import List, Dict
import pandas as pd
from .blynk_http_service import get_blynk_http_service

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
async def receive(payload: schemas.Payload, background_tasks: BackgroundTasks, patient_id: int = None, db: Session = Depends(get_db)):
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
            patient_id=patient_id,  # Associate with patient
            timestamp=r.timestamp,
            # Right foot
            big_toe=r.bigToe,
            pinky_toe=r.pinkyToe,
            meta_out=r.metaOut,
            meta_in=r.metaIn,
            heel=r.heel,
            # Left foot
            big_toe_l=r.bigToe_L,
            pinky_toe_l=r.pinkyToe_L,
            meta_out_l=r.metaOut_L,
            meta_in_l=r.metaIn_L,
            heel_l=r.heel_L,
        )
        db.add(row)
        rows.append(row)

    db.commit()
    for row in rows:
        db.refresh(row)

    # Auto-update Blynk in background (real-time push) - for specific patient if provided
    if patient_id:
        background_tasks.add_task(auto_update_blynk, patient_id=patient_id)
    else:
        background_tasks.add_task(auto_update_blynk)

    return {"status": "ok", "inserted": len(rows)}

@app.get("/api/readings", response_model=List[schemas.Sample])
def get_readings(limit: int = 50, patient_id: int = None, db: Session = Depends(get_db)):
    q = db.query(models.PressureSample)
    
    # Filter by patient_id if provided
    if patient_id is not None:
        q = q.filter(models.PressureSample.patient_id == patient_id)
    
    q = q.order_by(models.PressureSample.timestamp.desc()).limit(limit)
    results = list(q)
    results.reverse()  # chronological order

    # Convert DB rows to API schema
    response = []
    for r in results:
        response.append(
            schemas.Sample(
                timestamp=r.timestamp,
                pressures=schemas.PressureSet(
                    # Right foot
                    bigToe=r.big_toe,
                    pinkyToe=r.pinky_toe,
                    metaOut=r.meta_out,
                    metaIn=r.meta_in,
                    heel=r.heel,
                    # Left foot
                    bigToe_L=r.big_toe_l or 0.0,
                    pinkyToe_L=r.pinky_toe_l or 0.0,
                    metaOut_L=r.meta_out_l or 0.0,
                    metaIn_L=r.meta_in_l or 0.0,
                    heel_L=r.heel_l or 0.0
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
                # Right foot
                s1=r.big_toe,
                s2=r.pinky_toe,
                s3=r.meta_out,
                s4=r.meta_in,
                s5=r.heel,
                # Left foot
                s6=r.big_toe_l or 0.0,
                s7=r.pinky_toe_l or 0.0,
                s8=r.meta_out_l or 0.0,
                s9=r.meta_in_l or 0.0,
                s10=r.heel_l or 0.0,
            )
        )
    return response


@app.get("/api/gait-metrics")
def get_gait_metrics(limit: int = 100, db: Session = Depends(get_db)) -> Dict:
    """
    Calculate and return gait metrics and pressure ratings from recent readings.
    Also sends data to Blynk automatically.
    """
    # Fetch recent readings
    q = db.query(models.PressureSample).order_by(models.PressureSample.timestamp.desc()).limit(limit)
    results = list(q)
    
    if not results:
        raise HTTPException(status_code=404, detail="No pressure data available")
    
    results.reverse()  # chronological order
    
    # Convert to DataFrame
    data = []
    for r in results:
        data.append({
            'timestamp': r.timestamp,
            'bigToe': r.big_toe,
            'pinkyToe': r.pinky_toe,
            'metaOut': r.meta_out,
            'metaIn': r.meta_in,
            'heel': r.heel,
            'bigToe_L': r.big_toe_l or 0.0,
            'pinkyToe_L': r.pinky_toe_l or 0.0,
            'metaOut_L': r.meta_out_l or 0.0,
            'metaIn_L': r.meta_in_l or 0.0,
            'heel_L': r.heel_l or 0.0,
        })
    
    df = pd.DataFrame(data)
    
    # Calculate and send to Blynk
    blynk_service = get_blynk_http_service()
    result = blynk_service.process_and_send(df)
    
    return result


def auto_update_blynk(limit: int = 100, patient_id: int = None):
    """
    Background task to automatically update Blynk with latest metrics.
    Called automatically after ESP32 sends data for real-time updates.
    
    Args:
        limit: Number of recent samples to analyze
        patient_id: Optional patient ID to filter data
    """
    try:
        db = SessionLocal()
        
        # Fetch recent readings
        q = db.query(models.PressureSample)
        
        # Filter by patient if provided
        if patient_id is not None:
            q = q.filter(models.PressureSample.patient_id == patient_id)
        
        q = q.order_by(models.PressureSample.timestamp.desc()).limit(limit)
        results = list(q)
        
        if not results or len(results) < 50:  # Need minimum data for analysis
            db.close()
            return
        
        results.reverse()
        
        # Convert to DataFrame
        data = []
        for r in results:
            data.append({
                'timestamp': r.timestamp,
                'bigToe': r.big_toe,
                'pinkyToe': r.pinky_toe,
                'metaOut': r.meta_out,
                'metaIn': r.meta_in,
                'heel': r.heel,
                'bigToe_L': r.big_toe_l or 0.0,
                'pinkyToe_L': r.pinky_toe_l or 0.0,
                'metaOut_L': r.meta_out_l or 0.0,
                'metaIn_L': r.meta_in_l or 0.0,
                'heel_L': r.heel_l or 0.0,
            })
        
        df = pd.DataFrame(data)
        
        # Calculate and send to Blynk
        blynk_service = get_blynk_http_service()
        blynk_service.process_and_send(df)
        
        db.close()
        
    except Exception as e:
        print(f"Background Blynk update failed: {e}")


@app.post("/api/blynk/update")
async def update_blynk(limit: int = 100, db: Session = Depends(get_db)) -> Dict:
    """
    Manually trigger Blynk update with latest gait metrics.
    Use this endpoint to force an immediate update to Blynk.
    """
    try:
        # Fetch recent readings
        q = db.query(models.PressureSample).order_by(models.PressureSample.timestamp.desc()).limit(limit)
        results = list(q)
        
        if not results:
            return {"status": "error", "message": "No pressure data available"}
        
        results.reverse()
        
        # Convert to DataFrame
        data = []
        for r in results:
            data.append({
                'timestamp': r.timestamp,
                'bigToe': r.big_toe,
                'pinkyToe': r.pinky_toe,
                'metaOut': r.meta_out,
                'metaIn': r.meta_in,
                'heel': r.heel,
                'bigToe_L': r.big_toe_l or 0.0,
                'pinkyToe_L': r.pinky_toe_l or 0.0,
                'metaOut_L': r.meta_out_l or 0.0,
                'metaIn_L': r.meta_in_l or 0.0,
                'heel_L': r.heel_l or 0.0,
            })
        
        df = pd.DataFrame(data)
        
        # Calculate and send
        blynk_service = get_blynk_http_service()
        result = blynk_service.process_and_send(df)
        
        return {
            "status": "success",
            "data_points_analyzed": len(df),
            "ratings": result['ratings'],
            "metrics": result['metrics'],
            "blynk_sent": result['blynk_sent']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update Blynk: {str(e)}")


# Patient Management Endpoints

@app.get("/api/patients", response_model=List[schemas.PatientResponse])
def get_patients(db: Session = Depends(get_db)):
    """Get all patients"""
    patients = db.query(models.Patient).order_by(models.Patient.created_at.desc()).all()
    return patients

@app.post("/api/patients", response_model=schemas.PatientResponse, status_code=201)
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    """Create a new patient"""
    db_patient = models.Patient(
        name=patient.name,
        age=patient.age,
        notes=patient.notes
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.get("/api/patients/{patient_id}", response_model=schemas.PatientResponse)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    """Get a specific patient by ID"""
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@app.delete("/api/patients/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    """Delete a patient and all their pressure samples"""
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Delete all pressure samples for this patient
    db.query(models.PressureSample).filter(models.PressureSample.patient_id == patient_id).delete()
    
    # Delete the patient
    db.delete(patient)
    db.commit()
    return {"status": "deleted", "patient_id": patient_id}

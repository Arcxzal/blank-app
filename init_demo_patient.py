"""
Initialize database with a demo patient
Run this once to create initial patient records
"""
import sys
sys.path.append('/workspaces/blank-app')

from backend.database import SessionLocal, engine
from backend import models

# Create tables
models.Base.metadata.create_all(bind=engine)

def init_demo_patient():
    db = SessionLocal()
    
    try:
        # Check if demo patient already exists
        existing = db.query(models.Patient).filter(models.Patient.name == "John Doe (Demo)").first()
        
        if existing:
            print(f"✅ Demo patient already exists: ID={existing.id}, Name={existing.name}")
            return existing.id
        
        # Create demo patient
        demo_patient = models.Patient(
            name="John Doe (Demo)",
            age=45,
            notes="Demo patient for testing - pre-configured with sample data"
        )
        
        db.add(demo_patient)
        db.commit()
        db.refresh(demo_patient)
        
        print(f"✅ Created demo patient: ID={demo_patient.id}, Name={demo_patient.name}")
        return demo_patient.id
        
    except Exception as e:
        print(f"❌ Error creating demo patient: {e}")
        db.rollback()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing database with demo patient...")
    patient_id = init_demo_patient()
    if patient_id:
        print(f"\n✅ Setup complete! Demo patient ID: {patient_id}")
        print("\nYou can now:")
        print("1. View this patient in the Streamlit app")
        print("2. Send data from ESP32 with patient_id={patient_id}")
        print(f"3. Test API: curl https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/patients/{patient_id}")
    else:
        print("\n❌ Setup failed")

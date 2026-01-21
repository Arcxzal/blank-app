from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PressureSet(BaseModel):
    # Right foot sensors
    bigToe: float
    pinkyToe: float
    metaOut: float
    metaIn: float
    heel: float
    # Left foot sensors (optional for backwards compatibility)
    bigToe_L: float = 0.0
    pinkyToe_L: float = 0.0
    metaOut_L: float = 0.0
    metaIn_L: float = 0.0
    heel_L: float = 0.0

class Sample(BaseModel):
    timestamp: datetime
    pressures: PressureSet
    # Backwards-compatibility: older clients/endpoints expect a top-level
    # `sensor` attribute on each sample. Make it optional so code that
    # references `sample.sensor` won't raise AttributeError.
    sensor: Optional[int] = None
    mux: Optional[int] = None


class SimpleReading(BaseModel):
    """Compact numeric reading format from ESP32: timestamp as number and s1..s10 sensors"""
    timestamp: int
    # Right foot sensors
    s1: float
    s2: float
    s3: float
    s4: float
    s5: float
    # Left foot sensors (optional for backwards compatibility)
    s6: float = 0.0
    s7: float = 0.0
    s8: float = 0.0
    s9: float = 0.0
    s10: float = 0.0


class Reading(BaseModel):
    """Normalized reading with datetime and named sensor fields"""
    timestamp: datetime
    # Right foot sensors
    bigToe: float
    pinkyToe: float
    metaOut: float
    metaIn: float
    heel: float
    # Left foot sensors (optional for backwards compatibility)
    bigToe_L: float = 0.0
    pinkyToe_L: float = 0.0
    metaOut_L: float = 0.0
    metaIn_L: float = 0.0
    heel_L: float = 0.0

class Payload(BaseModel):
    device_id: str
    # Support both legacy `samples` (nested pressures) and new compact `readings`
    sample_count: Optional[int] = None
    samples: Optional[List[Sample]] = None
    readings: Optional[List[SimpleReading]] = None

    def get_readings(self) -> List[Reading]:
        """Return a list of normalized `Reading` objects.

        - If `readings` (compact format) is present, convert s1..s10 -> sensors.
        - If `samples` (legacy nested format) is present, convert those.
        """
        out: List[Reading] = []
        if self.readings:
            for r in self.readings:
                ts = r.timestamp
                # Handle possible millisecond timestamps
                if ts > 1_000_000_000_000:
                    dt = datetime.fromtimestamp(ts / 1000.0)
                else:
                    dt = datetime.fromtimestamp(ts)
                out.append(
                    Reading(
                        timestamp=dt,
                        # Right foot
                        bigToe=r.s1,
                        pinkyToe=r.s2,
                        metaOut=r.s3,
                        metaIn=r.s4,
                        heel=r.s5,
                        # Left foot
                        bigToe_L=r.s6,
                        pinkyToe_L=r.s7,
                        metaOut_L=r.s8,
                        metaIn_L=r.s9,
                        heel_L=r.s10,
                    )
                )
            return out

        if self.samples:
            for s in self.samples:
                out.append(
                    Reading(
                        timestamp=s.timestamp,
                        # Right foot
                        bigToe=s.pressures.bigToe,
                        pinkyToe=s.pressures.pinkyToe,
                        metaOut=s.pressures.metaOut,
                        metaIn=s.pressures.metaIn,
                        heel=s.pressures.heel,
                        # Left foot
                        bigToe_L=s.pressures.bigToe_L,
                        pinkyToe_L=s.pressures.pinkyToe_L,
                        metaOut_L=s.pressures.metaOut_L,
                        metaIn_L=s.pressures.metaIn_L,
                        heel_L=s.pressures.heel_L,
                    )
                )
        return out

# Backwards-compatibility alias: some endpoints/clients expect `ReadingOut`.
ReadingOut = Sample

# Patient schemas
class PatientBase(BaseModel):
    name: str
    age: Optional[int] = None
    notes: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

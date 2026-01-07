from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PressureSet(BaseModel):
    bigToe: float
    pinkyToe: float
    metaOut: float
    metaIn: float
    heel: float

class Sample(BaseModel):
    timestamp: datetime
    pressures: PressureSet
    # Backwards-compatibility: older clients/endpoints expect a top-level
    # `sensor` attribute on each sample. Make it optional so code that
    # references `sample.sensor` won't raise AttributeError.
    sensor: Optional[int] = None
    mux: Optional[int] = None


class SimpleReading(BaseModel):
    """Compact numeric reading format from ESP32: timestamp as number and s1..s5 sensors"""
    timestamp: int
    s1: float
    s2: float
    s3: float
    s4: float
    s5: float


class Reading(BaseModel):
    """Normalized reading with datetime and named sensor fields"""
    timestamp: datetime
    bigToe: float
    pinkyToe: float
    metaOut: float
    metaIn: float
    heel: float

class Payload(BaseModel):
    device_id: str
    # Support both legacy `samples` (nested pressures) and new compact `readings`
    sample_count: Optional[int] = None
    samples: Optional[List[Sample]] = None
    readings: Optional[List[SimpleReading]] = None

    def get_readings(self) -> List[Reading]:
        """Return a list of normalized `Reading` objects.

        - If `readings` (compact format) is present, convert s1..s5 -> sensors.
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
                        bigToe=r.s1,
                        pinkyToe=r.s2,
                        metaOut=r.s3,
                        metaIn=r.s4,
                        heel=r.s5,
                    )
                )
            return out

        if self.samples:
            for s in self.samples:
                out.append(
                    Reading(
                        timestamp=s.timestamp,
                        bigToe=s.pressures.bigToe,
                        pinkyToe=s.pressures.pinkyToe,
                        metaOut=s.pressures.metaOut,
                        metaIn=s.pressures.metaIn,
                        heel=s.pressures.heel,
                    )
                )
        return out

# Backwards-compatibility alias: some endpoints/clients expect `ReadingOut`.
ReadingOut = Sample

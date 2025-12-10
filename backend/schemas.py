# backend/schemas.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ReadingIn(BaseModel):
    sensor: int
mux: Optional[int] = None
channel: Optional[int] = None
voltage: float


class Payload(BaseModel):
    device_id: str
timestamp: Optional[datetime] = None
readings: List[ReadingIn]


class ReadingOut(BaseModel):
    id: int
device_id: str
sensor: int
mux: Optional[int]
channel: Optional[int]
voltage: float
created_at: datetime


class Config:
    orm_mode = True
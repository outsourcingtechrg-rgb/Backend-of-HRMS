from datetime import time, datetime
from typing import Optional

from pydantic import BaseModel, field_serializer


class ShiftBase(BaseModel):
    name: str
    saturday_on: bool = False
    shift_start_timing: time
    shift_end_timing: time
    shift_late_on: Optional[time] = None
    total_hours: time
    allow_remote: bool = False
    extra_data: Optional[dict] = None

    @field_serializer('shift_start_timing', 'shift_end_timing', 'shift_late_on', 'total_hours')
    def serialize_time(self, value: Optional[time]) -> Optional[str]:
        """Serialize time objects to HH:MM:SS strings"""
        if value is None:
            return None
        return value.strftime('%H:%M:%S')


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(BaseModel):
    name: Optional[str] = None
    saturday_on: Optional[bool] = None
    shift_start_timing: Optional[time] = None
    shift_end_timing: Optional[time] = None
    shift_late_on: Optional[time] = None
    total_hours: Optional[time] = None
    allow_remote: Optional[bool] = None
    extra_data: Optional[dict] = None


class ShiftOut(ShiftBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AttendanceSyncBase(BaseModel):
    device_ip: str
    sync_interval_minutes: int = 10
    is_enabled: bool = True


class AttendanceSyncCreate(AttendanceSyncBase):
    pass


class AttendanceSyncUpdate(BaseModel):
    device_ip: Optional[str] = None
    sync_interval_minutes: Optional[int] = None
    is_enabled: Optional[bool] = None
    last_synced_at: Optional[datetime] = None


class AttendanceSyncResponse(BaseModel):
    id: int
    device_ip: str
    sync_interval_minutes: int
    is_enabled: bool
    created_at: datetime
    updated_at: datetime
    last_synced_at: datetime | None = None

    class Config:
        from_attributes = True
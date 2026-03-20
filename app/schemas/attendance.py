from datetime import date, datetime, time
from typing import Optional
from pydantic import BaseModel
from app.models.attendance import AttendanceModeEnum


class AttendanceBase(BaseModel):
    employee_id: int
    employee_name: str
    attendance_date: date
    attendance_time: time
    punch: bool
    attendance_mode: AttendanceModeEnum = AttendanceModeEnum.onsite
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ip_address: Optional[str] = None
    extra_data: Optional[dict] = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    attendance_date: Optional[date] = None
    attendance_time: Optional[time] = None
    punch: Optional[bool] = None
    attendance_mode: Optional[AttendanceModeEnum] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ip_address: Optional[str] = None
    extra_data: Optional[dict] = None


class AttendanceOut(AttendanceBase):
    id: int
    created_at: datetime
    synced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AttendanceRead(AttendanceOut):
    """Full attendance read schema"""
    
    class Config:
        from_attributes = True


class AttendanceBulkCreate(BaseModel):
    """Schema for bulk attendance creation from ZKT machine"""
    records: list[AttendanceCreate]


class AttendanceSyncStatus(BaseModel):
    """Schema for sync status information"""
    last_synced_at: Optional[datetime] = None
    total_records_synced: int = 0
    message: str = ""

# 🔹 Frontend Attendance Record (Processed)
class AttendanceRecord(BaseModel):
    id: int
    employee_id: int
    date: str
    status: str  # Present | Late | Absent | Leave
    in_time: Optional[str]
    out_time: Optional[str]
    hours: Optional[float]
    note: Optional[str] = None

    class Config:
        from_attributes = True


# 🔹 Summary
class AttendanceSummary(BaseModel):
    present: int
    late: int
    absent: int
    leave: int
    total_days: int
    rate: float


# 🔹 List Response (optional wrapper)
class AttendanceListResponse(BaseModel):
    data: list[AttendanceRecord]
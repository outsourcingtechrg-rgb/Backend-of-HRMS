from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field
from enum import Enum

class LeaveStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"

class LeaveCycleCreate(BaseModel):
    name: str
    start_month: int = Field(..., ge=1, le=12)
    start_day: int = Field(1, ge=1, le=31)
    end_month: int = Field(..., ge=1, le=12)
    end_day: int = Field(31, ge=1, le=31)

class LeaveCycleOut(BaseModel):
    id: int
    name: str
    start_month: int
    start_day: int
    end_month: int
    end_day: int
    is_active: bool

    class Config:
        from_attributes = True

class LeaveTypeCreate(BaseModel):
    name: str
    is_paid: bool = True
    max_per_cycle: float = 0
    carry_forward: bool = False
    max_carry_forward: float = 0
    leave_cycle_id: int

class LeaveTypeOut(BaseModel):
    id: int
    name: str
    is_paid: bool
    max_per_cycle: float
    carry_forward: bool
    max_carry_forward: float
    leave_cycle_id: int

    class Config:
        from_attributes = True

class LeaveBalanceOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    leave_cycle_id: int

    cycle_start_date: date
    cycle_end_date: date

    allocated: float
    used: float
    pending: float
    carry_forward: float

    remaining: float

    class Config:
        from_attributes = True

class LeaveBalanceSummary(BaseModel):
    leave_type: str
    allocated: float
    used: float
    pending: float
    remaining: float

class LeaveRequestCreate(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None
    is_half_day: bool = False

class LeaveAction(BaseModel):
    action: str  # "approve" or "reject"

class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    leave_cycle_id: int

    start_date: date
    end_date: date
    days: float

    is_half_day: bool
    reason: Optional[str]

    status: LeaveStatusEnum

    approved_by: Optional[int]
    approved_at: Optional[datetime]

    created_at: datetime

    class Config:
        from_attributes = True

class LeaveAuditLogOut(BaseModel):
    id: int
    leave_request_id: int
    action: str
    performed_by: int

    old_status: Optional[str]
    new_status: Optional[str]

    timestamp: datetime

    class Config:
        from_attributes = True
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GenderSpecific(str, Enum):
    ALL = "ALL"
    MALE = "MALE"
    FEMALE = "FEMALE"


class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Leave Cycle Schemas
# ---------------------------------------------------------------------------

class LeaveCycleBase(BaseModel):
    name: str
    start_date: date
    end_date: date
    is_active: bool = True

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class LeaveCycleCreate(LeaveCycleBase):
    pass


class LeaveCycleUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class LeaveCycleOut(LeaveCycleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Leave Type Schemas
# ---------------------------------------------------------------------------

class LeaveTypeBase(BaseModel):
    name: str
    gender_specific: GenderSpecific = GenderSpecific.ALL
    is_paid: bool = True
    min_days: int = 1
    max_per_use: int = 30
    total_per_cycle: int = 0
    requires_document: bool = False
    document_description: Optional[str] = None
    allowed_file_types: str = "pdf,jpg,png,doc,docx"

    @field_validator("min_days", "max_per_use", "total_per_cycle")
    @classmethod
    def positive_days(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Day values must be non-negative")
        return v


class LeaveTypeCreate(LeaveTypeBase):
    cycle_id: int


class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = None
    gender_specific: Optional[GenderSpecific] = None
    is_paid: Optional[bool] = None
    min_days: Optional[int] = None
    max_per_use: Optional[int] = None
    total_per_cycle: Optional[int] = None
    requires_document: Optional[bool] = None
    document_description: Optional[str] = None
    allowed_file_types: Optional[str] = None


class LeaveTypeOut(LeaveTypeBase):
    id: int
    cycle_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Leave Application / Transaction Schemas
# ---------------------------------------------------------------------------

class LeaveApplicationCreate(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    employee_note: Optional[str] = None

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LeaveApplicationOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    cycle_id: int
    start_date: date
    end_date: date
    requested_days: int
    status: LeaveStatus
    employee_note: Optional[str] = None
    hr_note: Optional[str] = None
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None
    leave_type: Optional[LeaveTypeOut] = None

    model_config = {"from_attributes": True}


class LeaveReviewRequest(BaseModel):
    hr_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Leave Attachment Schemas
# ---------------------------------------------------------------------------

class LeaveAttachmentOut(BaseModel):
    id: int
    transaction_id: int
    file_name: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    file_extension: Optional[str] = None
    description: Optional[str] = None
    uploaded_by: Optional[int] = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Leave Summary Schemas
# ---------------------------------------------------------------------------

class LeaveTypeSummary(BaseModel):
    leave_type_id: int
    leave_type_name: str
    total_allocated: int
    total_taken: int
    total_pending: int
    remaining: int


class LeaveSummaryOut(BaseModel):
    employee_id: int
    cycle_id: int
    cycle_name: str
    summaries: List[LeaveTypeSummary]


# ---------------------------------------------------------------------------
# Dashboard Stats Schemas
# ---------------------------------------------------------------------------

class ApprovedRejectedRatio(BaseModel):
    approved: int
    rejected: int
    ratio: float  # approved / (approved + rejected) * 100


class DepartmentUsage(BaseModel):
    department: str
    total_leaves: int


class MonthlyTrend(BaseModel):
    month: str        # "2024-01"
    total_leaves: int


class DashboardStatsOut(BaseModel):
    total_leaves_taken: int
    pending_approvals: int
    approved_vs_rejected: ApprovedRejectedRatio
    department_usage: List[DepartmentUsage]
    monthly_trend: List[MonthlyTrend]
"""
app/schemas/application.py

Pydantic schemas for the Application module.

Request bodies  → ApplicationCreate, HODActionIn, HRActionIn
Response shapes → ApplicationOut (full), ApplicationListItem (table row)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ─── Enums (re-exported for router use) ──────────────────────────
from app.models.application import ApplicationTypeEnum, ApplicationStatusEnum


# ─── Shared employee mini-shape (nested in responses) ────────────
class EmployeeMini(BaseModel):
    id:          int
    f_name:      str
    l_name:      str
    designation: Optional[str] = None
    image:       Optional[str] = None

    @property
    def full_name(self) -> str:
        return f"{self.f_name} {self.l_name}".strip()

    model_config = {"from_attributes": True}


# ─── CREATE ──────────────────────────────────────────────────────
class ApplicationCreate(BaseModel):
    """
    Submitted by the employee.
    employee_id is injected by the router (from JWT), not from body.
    """
    type:        ApplicationTypeEnum
    from_date:   date
    to_date:     date
    reason:      str = Field(..., min_length=5, max_length=2000)

    # Reimbursement only
    amount:      Optional[Decimal] = Field(None, ge=0, decimal_places=2)

    # Travel only
    destination: Optional[str] = Field(None, max_length=255)

    extra_data:  Optional[dict] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ApplicationCreate":
        if self.to_date < self.from_date:
            raise ValueError("to_date must be on or after from_date")
        return self

    @model_validator(mode="after")
    def validate_type_fields(self) -> "ApplicationCreate":
        if self.type == ApplicationTypeEnum.reimbursement and self.amount is None:
            raise ValueError("amount is required for Reimbursement applications")
        if self.type == ApplicationTypeEnum.travel and not self.destination:
            raise ValueError("destination is required for Travel applications")
        return self


# ─── HOD ACTION ──────────────────────────────────────────────────
class HODActionIn(BaseModel):
    """
    Body sent by a Head of Department when reviewing a pending application.
    action = "approve" | "reject"
    rejection_reason is required when action = "reject".
    """
    action:           str = Field(..., pattern="^(approve|reject)$")
    rejection_reason: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def reason_required_on_reject(self) -> "HODActionIn":
        if self.action == "reject" and not self.rejection_reason:
            raise ValueError("rejection_reason is required when action is 'reject'")
        return self


# ─── HR ACTION ───────────────────────────────────────────────────
class HRActionIn(BaseModel):
    """
    Body sent by HR (or Super Admin / CEO) for final decision.
    Can act on Pending (direct, when no HOD) or HOD_Approved applications.
    """
    action:           str = Field(..., pattern="^(approve|reject)$")
    rejection_reason: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def reason_required_on_reject(self) -> "HRActionIn":
        if self.action == "reject" and not self.rejection_reason:
            raise ValueError("rejection_reason is required when action is 'reject'")
        return self


# ─── UPDATE (employee edits their own pending application) ───────
class ApplicationUpdate(BaseModel):
    from_date:   Optional[date]    = None
    to_date:     Optional[date]    = None
    reason:      Optional[str]     = Field(None, min_length=5, max_length=2000)
    amount:      Optional[Decimal] = Field(None, ge=0)
    destination: Optional[str]     = Field(None, max_length=255)
    extra_data:  Optional[dict]    = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ApplicationUpdate":
        if self.from_date and self.to_date and self.to_date < self.from_date:
            raise ValueError("to_date must be on or after from_date")
        return self


# ─── RESPONSE — full detail ───────────────────────────────────────
class ApplicationOut(BaseModel):
    id:          int
    employee_id: int
    type:        ApplicationTypeEnum
    status:      ApplicationStatusEnum

    from_date:   date
    to_date:     date
    reason:      str

    amount:      Optional[Decimal] = None
    destination: Optional[str]     = None

    # HOD step
    hod_action_by:       Optional[int]      = None
    hod_action_at:       Optional[datetime] = None
    hod_rejection_reason: Optional[str]     = None

    # HR / final step
    hr_action_by:        Optional[int]      = None
    hr_action_at:        Optional[datetime] = None
    hr_rejection_reason: Optional[str]      = None

    created_at:  datetime
    updated_at:  Optional[datetime] = None
    extra_data:  Optional[dict]     = None

    # Nested employee objects (populated by router via ORM joins)
    employee:     Optional[EmployeeMini] = None
    hod_actioner: Optional[EmployeeMini] = None
    hr_actioner:  Optional[EmployeeMini] = None

    model_config = {"from_attributes": True}


# ─── RESPONSE — table list row (lightweight) ─────────────────────
class ApplicationListItem(BaseModel):
    """
    Lightweight shape for the admin table.
    employee_name and department_name are injected by the CRUD layer.
    """
    id:              int
    employee_id:     int
    employee_name:   Optional[str] = None
    department_name: Optional[str] = None
    employee_image:  Optional[str] = None

    type:   ApplicationTypeEnum
    status: ApplicationStatusEnum

    from_date: date
    to_date:   date
    reason:    str

    amount:      Optional[Decimal] = None
    destination: Optional[str]     = None

    hod_rejection_reason: Optional[str] = None
    hr_rejection_reason:  Optional[str] = None

    # Who did what (names, not just IDs)
    hod_actioner_name: Optional[str] = None
    hr_actioner_name:  Optional[str] = None

    created_at: datetime

    model_config = {"from_attributes": True}


# ─── STATS ───────────────────────────────────────────────────────
class ApplicationStats(BaseModel):
    total:        int
    pending:      int
    hod_approved: int
    hod_rejected: int
    approved:     int
    rejected:     int
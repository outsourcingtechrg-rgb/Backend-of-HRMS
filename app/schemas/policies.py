"""
app/schemas/policy.py  — UPDATED

New fields added to all response shapes:
  approved_by        — employee id of CEO approver
  approved_by_name   — full name of CEO approver
  approved_at        — approval timestamp
  approval_note      — CEO's optional note
  submitted_for_review_at — when HR submitted

New request schemas:
  PolicySubmitReview  — HR submits draft for CEO review (optional note)
  PolicyApprove       — CEO approves (with optional note)
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.policy import PolicyStatusEnum, PolicyCategoryEnum


# ─── CREATE ──────────────────────────────────────────────────────
class PolicyCreate(BaseModel):
    title:     str                = Field(..., min_length=3, max_length=500)
    summary:   str                = Field(..., min_length=5)
    content:   str                = Field(..., min_length=10)
    version:   str                = Field("v1.0", max_length=20)
    category:  PolicyCategoryEnum = PolicyCategoryEnum.hr_policy
    status:    PolicyStatusEnum   = PolicyStatusEnum.draft
    audience:  str                = Field("All Employees", max_length=100)
    mandatory: bool               = False
    pinned:    bool               = False
    extra_data: Optional[dict]    = None


# ─── UPDATE ──────────────────────────────────────────────────────
class PolicyUpdate(BaseModel):
    title:     Optional[str]               = Field(None, min_length=3, max_length=500)
    summary:   Optional[str]               = Field(None, min_length=5)
    content:   Optional[str]               = Field(None, min_length=10)
    version:   Optional[str]               = Field(None, max_length=20)
    category:  Optional[PolicyCategoryEnum] = None
    status:    Optional[PolicyStatusEnum]   = None
    audience:  Optional[str]               = Field(None, max_length=100)
    mandatory: Optional[bool]              = None
    pinned:    Optional[bool]              = None
    extra_data: Optional[dict]             = None


# ─── SUBMIT FOR REVIEW ───────────────────────────────────────────
class PolicySubmitReview(BaseModel):
    """HR submits a Draft policy for CEO review."""
    note: Optional[str] = Field(None, max_length=1000)


# ─── APPROVE ─────────────────────────────────────────────────────
class PolicyApprove(BaseModel):
    """CEO approves a policy in Review status."""
    note: Optional[str] = Field(None, max_length=1000)


# ─── RESPONSE — list item ─────────────────────────────────────────
class PolicyListItem(BaseModel):
    id:               int
    title:            str
    category:         str
    status:           str
    audience:         str
    version:          str
    mandatory:        bool
    pinned:           bool
    summary:          str
    created_by:       Optional[int]      = None
    created_by_name:  Optional[str]      = None
    created_at:       Optional[datetime] = None
    updated_at:       Optional[datetime] = None
    ack_count:        int                = 0
    total_recipients: int                = 0

    # ── Approval workflow ──
    approved_by:       Optional[int]      = None
    approved_by_name:  Optional[str]      = None
    approved_at:       Optional[datetime] = None
    approval_note:     Optional[str]      = None
    submitted_for_review_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── RESPONSE — full detail ───────────────────────────────────────
class PolicyOut(BaseModel):
    id:               int
    title:            str
    category:         str
    status:           str
    audience:         str
    version:          str
    mandatory:        bool
    pinned:           bool
    summary:          str
    content:          str
    created_by:       Optional[int]      = None
    created_by_name:  Optional[str]      = None
    created_at:       Optional[datetime] = None
    updated_at:       Optional[datetime] = None
    ack_count:        int                = 0
    total_recipients: int                = 0
    extra_data:       Optional[dict]     = None

    # ── Approval workflow ──
    approved_by:       Optional[int]      = None
    approved_by_name:  Optional[str]      = None
    approved_at:       Optional[datetime] = None
    approval_note:     Optional[str]      = None
    submitted_for_review_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── STATS ───────────────────────────────────────────────────────
class PolicyStats(BaseModel):
    total:        int
    active:       int
    draft:        int
    review:       int
    archived:     int
    mandatory:    int
    avg_ack_rate: float
    pending_approval: int     # policies in "Review" status (CEO dashboard)


# ─── ACKNOWLEDGE ─────────────────────────────────────────────────
class AcknowledgeOut(BaseModel):
    policy_id:   int
    employee_id: int
    acked_at:    datetime

    model_config = {"from_attributes": True}


# ─── EMPLOYEE POLICY (with ack status) ──────────────────────────
class EmployeePolicyItem(BaseModel):
    """
    Shape returned by GET /policies/my — employee-facing list.
    Includes whether THIS employee has acknowledged the policy.
    """
    id:               int
    title:            str
    category:         str
    status:           str
    audience:         str
    version:          str
    mandatory:        bool
    pinned:           bool
    summary:          str
    created_at:       Optional[datetime] = None
    updated_at:       Optional[datetime] = None
    ack_count:        int                = 0
    total_recipients: int                = 0

    # Key field for employee view
    acknowledged:     bool               = False
    acked_at:         Optional[datetime] = None

    model_config = {"from_attributes": True}

    
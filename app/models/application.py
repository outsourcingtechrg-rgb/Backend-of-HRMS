
"""
app/models/application.py

Application model — Leave, Travel, Reimbursement requests.

Approval hierarchy
──────────────────
  Employee / Intern / Lead
      ↓  submits to HOD (dept head of their dept) for first-level review
      ↓  HOD: Approve → goes to HR for final approval
             Reject  → done (terminal rejection)
  HR Admin / HR Officer
      ↓  gives final Approve / Reject
  CEO / Super Admin
      ↓  can see and action everything

Status flow
───────────
  Pending            → initial state
  HOD_Approved       → HOD approved; awaiting HR decision
  HOD_Rejected       → HOD rejected; terminal
  Approved           → HR gave final approval; terminal
  Rejected           → HR rejected after HOD approval (or HR direct); terminal

  If the employee has no HOD (department has no head) the application
  goes directly to Pending and HR picks it up immediately.
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ApplicationTypeEnum(str, enum.Enum):
    leave         = "Leave"
    travel        = "Travel"
    reimbursement = "Reimbursement"


class ApplicationStatusEnum(str, enum.Enum):
    pending      = "Pending"
    hod_approved = "HOD_Approved"   # HOD cleared; waiting for HR
    hod_rejected = "HOD_Rejected"   # HOD rejected; terminal
    approved     = "Approved"       # HR final approval; terminal
    rejected     = "Rejected"       # HR rejected; terminal


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)

    # ── Submitter ──────────────────────────────────────────
    employee_id = Column(
        Integer,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Request details ────────────────────────────────────
    type = Column(
        SQLEnum(ApplicationTypeEnum, name="application_type_enum"),
        nullable=False,
        index=True,
    )

    from_date   = Column(Date,    nullable=False)
    to_date     = Column(Date,    nullable=False)
    reason      = Column(Text,    nullable=False)

    # Optional: amount for Reimbursement type
    amount      = Column(Numeric(10, 2), nullable=True)

    # Optional: destination for Travel type
    destination = Column(String(255), nullable=True)

    # ── Status ─────────────────────────────────────────────
    status = Column(
        SQLEnum(ApplicationStatusEnum, name="application_status_enum"),
        nullable=False,
        default=ApplicationStatusEnum.pending,
        index=True,
    )

    # ── HOD action ─────────────────────────────────────────
    hod_action_by = Column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    hod_action_at     = Column(DateTime, nullable=True)
    hod_rejection_reason = Column(Text, nullable=True)

    # ── HR / final action ──────────────────────────────────
    hr_action_by = Column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    hr_action_at       = Column(DateTime, nullable=True)
    hr_rejection_reason = Column(Text, nullable=True)

    # ── Audit ──────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True,  onupdate=func.now())
    is_deleted = Column(Boolean,  nullable=False, default=False)

    # Optional arbitrary metadata
    extra_data = Column(JSON, nullable=True)

    # ── ORM relationships ──────────────────────────────────
    employee = relationship(
        "Employee",
        foreign_keys=[employee_id],
        back_populates="applications",
    )

    hod_actioner = relationship(
        "Employee",
        foreign_keys=[hod_action_by],
    )

    hr_actioner = relationship(
        "Employee",
        foreign_keys=[hr_action_by],
    )
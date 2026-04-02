"""
app/models/policy.py

Policy model — company-wide policy documents with acknowledgement tracking.

Tables
──────
  policies              — the policy document itself
  policy_acknowledgements — per-employee read/ack records

Policy lifecycle
────────────────
  Draft    → author is still writing; not visible to employees
  Review   → submitted for HR / legal review before publishing
  Active   → published and visible to all target employees
  Archived → no longer current; hidden from employee views but kept for audit

Audience
────────
  "All Employees" broadcasts to everyone.
  Any other value (e.g. "HR", "Engineering") scopes to a department name
  or role name — the frontend string is stored verbatim and matched by
  the employee-facing endpoint.

Acknowledgement
───────────────
  When an employee clicks "Acknowledge" in MyPoliciesPage, the
  frontend POSTs to /policies/{id}/acknowledge.
  One row per (policy_id, employee_id) — unique constraint prevents
  duplicates.  ack_count is a computed property on the CRUD layer
  (COUNT of non-deleted ack rows).
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class PolicyStatusEnum(str, enum.Enum):
    draft    = "Draft"
    review   = "Review"
    active   = "Active"
    archived = "Archived"


class PolicyCategoryEnum(str, enum.Enum):
    hr_policy       = "HR Policy"
    it_security     = "IT & Security"
    finance         = "Finance"
    legal           = "Legal"
    health_safety   = "Health & Safety"
    operations      = "Operations"
    code_of_conduct = "Code of Conduct"
    benefits        = "Benefits"


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)

    # ── Content ───────────────────────────────────────────────────
    title    = Column(String(500), nullable=False, index=True)
    summary  = Column(Text,        nullable=False)          # short description shown in list
    content  = Column(Text,        nullable=False)          # full policy body
    version  = Column(String(20),  nullable=False, default="v1.0")

    # ── Classification ────────────────────────────────────────────
    category = Column(
        SQLEnum(PolicyCategoryEnum, name="policy_category_enum"),
        nullable=False,
        default=PolicyCategoryEnum.hr_policy,
        index=True,
    )
    status = Column(
        SQLEnum(PolicyStatusEnum, name="policy_status_enum"),
        nullable=False,
        default=PolicyStatusEnum.draft,
        index=True,
    )

    # ── Visibility ────────────────────────────────────────────────
    # Audience is stored as a plain string matching frontend values:
    # "All Employees", "HR", "Engineering", "Finance", etc.
    audience  = Column(String(100), nullable=False, default="All Employees")
    mandatory = Column(Boolean, nullable=False, default=False)
    pinned    = Column(Boolean, nullable=False, default=False)

    # ── Authorship ────────────────────────────────────────────────
    created_by = Column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    approved_by = Column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at = Column(DateTime, nullable=True)
    approval_note = Column(Text, nullable=True)
    submitted_for_review_at = Column(DateTime, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True,  onupdate=func.now())
    is_deleted = Column(Boolean,  nullable=False, default=False)

    # Optional free-form metadata (tags, related links, etc.)
    extra_data = Column(JSON, nullable=True)

        # ── ORM relationships ─────────────────────────────────────────

    author = relationship(
        "Employee",
        foreign_keys=[created_by],
        backref="policies_created"
    )

    approver = relationship(
        "Employee",
        foreign_keys=[approved_by],
        backref="policies_approved"
    )

    acknowledgements = relationship(
        "PolicyAcknowledgement",
        back_populates="policy",
        cascade="all, delete-orphan",
    )
 
class PolicyAcknowledgement(Base):
    """
    One row per employee who has acknowledged a policy.
    Unique on (policy_id, employee_id) — duplicates are rejected at the DB level.
    """
    __tablename__ = "policy_acknowledgements"
    __table_args__ = (
        UniqueConstraint("policy_id", "employee_id", name="uq_policy_ack"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    policy_id  = Column(Integer, ForeignKey("policies.id",   ondelete="CASCADE"), nullable=False, index=True)
    employee_id= Column(Integer, ForeignKey("employees.id",  ondelete="CASCADE"), nullable=False, index=True)
    acked_at   = Column(DateTime, nullable=False, server_default=func.now())

    # ── ORM relationships ─────────────────────────────────────────
    policy = relationship("Policy", back_populates="acknowledgements")
    employee = relationship("Employee", foreign_keys=[employee_id])
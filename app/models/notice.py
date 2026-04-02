"""
app/models/notice.py

Notice Board — company-wide and department-targeted announcements.

Tables
──────
  notices                   — the notice document
  notice_audience_depts     — M2M: which departments can see a notice
                              (only used when audience_type = "departments")
  notice_acknowledgements   — per-employee read/ack records

Audience types
──────────────
  all           → every active employee sees it
  departments   → only employees in specified department(s)
  roles         → only employees with specified role name(s)
  selective     → specific employee ids (stored as JSON in extra_data["employee_ids"])

Priority levels
───────────────
  low | medium | high | urgent

Category
────────
  General | HR | IT | Finance | Operations | Health & Safety | Event | Policy Update

Notice lifecycle
────────────────
  Notices are immediately live upon creation.
  is_deleted = True for soft-delete.
  expires_at (optional) — frontend hides expired notices for employees.
  pinned — float to top of list.

Who can create
──────────────
  level 1  Super Admin
  level 2  CEO
  level 3  HR Admin
  level 4  HR
  level 6  Department Head
  (checked in router, NOT in model)
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


class NoticePriorityEnum(str, enum.Enum):
    low    = "Low"
    medium = "Medium"
    high   = "High"
    urgent = "Urgent"


class NoticeCategoryEnum(str, enum.Enum):
    general        = "General"
    hr             = "HR"
    it             = "IT"
    finance        = "Finance"
    operations     = "Operations"
    health_safety  = "Health & Safety"
    event          = "Event"
    policy_update  = "Policy Update"


class NoticeAudienceTypeEnum(str, enum.Enum):
    all          = "all"
    departments  = "departments"
    roles        = "roles"
    selective    = "selective"


class Notice(Base):
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True)

    # ── Content ───────────────────────────────────────────────────
    title   = Column(String(500), nullable=False, index=True)
    content = Column(Text,        nullable=False)

    # ── Classification ────────────────────────────────────────────
    category = Column(
        SQLEnum(NoticeCategoryEnum, name="notice_category_enum"),
        nullable=False,
        default=NoticeCategoryEnum.general,
        index=True,
    )
    priority = Column(
        SQLEnum(NoticePriorityEnum, name="notice_priority_enum"),
        nullable=False,
        default=NoticePriorityEnum.medium,
        index=True,
    )

    # ── Audience ──────────────────────────────────────────────────
    audience_type = Column(
        SQLEnum(NoticeAudienceTypeEnum, name="notice_audience_type_enum"),
        nullable=False,
        default=NoticeAudienceTypeEnum.all,
        index=True,
    )
    # For audience_type = "roles": comma-separated or JSON list stored as text
    audience_roles = Column(Text, nullable=True)  # e.g. "HR,Engineering,Finance"

    # For audience_type = "selective": JSON list of employee ids
    # stored in extra_data["employee_ids"] = [1, 2, 3, ...]

    # ── Visibility ────────────────────────────────────────────────
    pinned    = Column(Boolean,  nullable=False, default=False)
    is_active = Column(Boolean,  nullable=False, default=True)   # quick enable/disable
    expires_at = Column(DateTime, nullable=True)                 # optional expiry
    send_email = Column(Boolean,  nullable=False, default=False) # whether to send email to recipients

    # ── Authorship ────────────────────────────────────────────────
    created_by = Column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Audit ─────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True,  onupdate=func.now())
    is_deleted = Column(Boolean,  nullable=False, default=False)

    # Free-form metadata (e.g. selective employee_ids, attachments)
    extra_data = Column(JSON, nullable=True)

    # ── ORM relationships ─────────────────────────────────────────
    author = relationship(
        "Employee",
        foreign_keys=[created_by],
    )
    audience_departments = relationship(
        "NoticeAudienceDept",
        back_populates="notice",
        cascade="all, delete-orphan",
    )
    acknowledgements = relationship(
        "NoticeAcknowledgement",
        back_populates="notice",
        cascade="all, delete-orphan",
    )


class NoticeAudienceDept(Base):
    """
    M2M junction: which departments can see a notice
    when audience_type = 'departments'.
    Stores department_id (FK to departments.id).
    """
    __tablename__ = "notice_audience_depts"
    __table_args__ = (
        UniqueConstraint("notice_id", "department_id", name="uq_notice_dept"),
    )

    id            = Column(Integer, primary_key=True, index=True)
    notice_id     = Column(Integer, ForeignKey("notices.id",     ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True)

    notice     = relationship("Notice",     back_populates="audience_departments")
    department = relationship("Department", foreign_keys=[department_id])


class NoticeAcknowledgement(Base):
    """
    One row per employee who has acknowledged a notice.
    Unique on (notice_id, employee_id).
    """
    __tablename__ = "notice_acknowledgements"
    __table_args__ = (
        UniqueConstraint("notice_id", "employee_id", name="uq_notice_ack"),
    )

    id          = Column(Integer,  primary_key=True, index=True)
    notice_id   = Column(Integer,  ForeignKey("notices.id",   ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer,  ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    acked_at    = Column(DateTime, nullable=False, server_default=func.now())

    notice   = relationship("Notice",   back_populates="acknowledgements")
    employee = relationship("Employee", foreign_keys=[employee_id])
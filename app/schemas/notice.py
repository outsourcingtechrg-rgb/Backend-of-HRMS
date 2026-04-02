"""
app/schemas/notice.py

Pydantic schemas for the Notice Board module.

Frontend ↔ Backend field mapping
─────────────────────────────────
  id                → id
  title             → title
  content           → content
  category          → category (NoticeCategoryEnum value)
  priority          → priority (NoticePriorityEnum value)
  audience_type     → audience_type ("all"|"departments"|"roles"|"selective")
  department_ids    → list of dept ids (for audience_type=departments)
  audience_roles    → comma-separated role names (for audience_type=roles)
  employee_ids      → list of employee ids (for audience_type=selective)
  pinned            → pinned
  is_active         → is_active
  expires_at        → expires_at (ISO datetime or null)
  created_by_name   → author full name (computed)
  ack_count         → count of acknowledgements (computed)
  total_recipients  → eligible employees (computed)
  acknowledged      → bool (employee-facing only)
  acked_at          → datetime (employee-facing only)
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.notice import (
    NoticePriorityEnum,
    NoticeCategoryEnum,
    NoticeAudienceTypeEnum,
)


# ─── CREATE ──────────────────────────────────────────────────────
class NoticeCreate(BaseModel):
    title:         str                    = Field(..., min_length=3, max_length=500)
    content:       str                    = Field(..., min_length=5)
    category:      NoticeCategoryEnum     = NoticeCategoryEnum.general
    priority:      NoticePriorityEnum     = NoticePriorityEnum.medium
    audience_type: NoticeAudienceTypeEnum = NoticeAudienceTypeEnum.all

    # Audience details — only one of these is used depending on audience_type
    department_ids: List[int]  = Field(default_factory=list)   # for type=departments
    audience_roles: List[str]  = Field(default_factory=list)   # for type=roles
    employee_ids:   List[int]  = Field(default_factory=list)   # for type=selective

    pinned:     bool              = False
    is_active:  bool              = True
    send_email: bool              = False    # whether to send email to recipients
    expires_at: Optional[datetime] = None
    extra_data: Optional[dict]    = None


# ─── UPDATE ──────────────────────────────────────────────────────
class NoticeUpdate(BaseModel):
    title:         Optional[str]                    = Field(None, min_length=3, max_length=500)
    content:       Optional[str]                    = Field(None, min_length=5)
    category:      Optional[NoticeCategoryEnum]     = None
    priority:      Optional[NoticePriorityEnum]     = None
    audience_type: Optional[NoticeAudienceTypeEnum] = None

    department_ids: Optional[List[int]]  = None
    audience_roles: Optional[List[str]]  = None
    employee_ids:   Optional[List[int]]  = None

    pinned:     Optional[bool]     = None
    is_active:  Optional[bool]     = None
    send_email: Optional[bool]     = None    # whether to send email to recipients
    expires_at: Optional[datetime] = None
    extra_data: Optional[dict]     = None


# ─── RESPONSE — department info ───────────────────────────────────
class DeptInfo(BaseModel):
    id:   int
    name: str

    model_config = {"from_attributes": True}


# ─── RESPONSE — list item ─────────────────────────────────────────
class NoticeListItem(BaseModel):
    id:               int
    title:            str
    category:         str
    priority:         str
    audience_type:    str
    pinned:           bool
    is_active:        bool
    send_email:       bool               = False
    expires_at:       Optional[datetime] = None
    created_by:       Optional[int]      = None
    created_by_name:  Optional[str]      = None
    created_at:       Optional[datetime] = None
    updated_at:       Optional[datetime] = None
    ack_count:        int                = 0
    total_recipients: int                = 0

    # Audience details
    department_ids:   List[int]  = Field(default_factory=list)
    department_names: List[str]  = Field(default_factory=list)
    audience_roles:   List[str]  = Field(default_factory=list)
    employee_ids:     List[int]  = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ─── RESPONSE — full detail ───────────────────────────────────────
class NoticeOut(BaseModel):
    id:               int
    title:            str
    content:          str
    category:         str
    priority:         str
    audience_type:    str
    pinned:           bool
    is_active:        bool
    send_email:       bool               = False
    expires_at:       Optional[datetime] = None
    created_by:       Optional[int]      = None
    created_by_name:  Optional[str]      = None
    created_at:       Optional[datetime] = None
    updated_at:       Optional[datetime] = None
    ack_count:        int                = 0
    total_recipients: int                = 0
    extra_data:       Optional[dict]     = None

    department_ids:   List[int]  = Field(default_factory=list)
    department_names: List[str]  = Field(default_factory=list)
    audience_roles:   List[str]  = Field(default_factory=list)
    employee_ids:     List[int]  = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ─── STATS ───────────────────────────────────────────────────────
class NoticeStats(BaseModel):
    total:    int
    active:   int
    pinned:   int
    urgent:   int
    avg_ack_rate: float


# ─── EMPLOYEE-FACING NOTICE ──────────────────────────────────────
class EmployeeNoticeItem(BaseModel):
    """
    Returned by GET /notices/my — includes acknowledgement status
    for the requesting employee.
    """
    id:               int
    title:            str
    content:          str
    category:         str
    priority:         str
    audience_type:    str
    pinned:           bool
    expires_at:       Optional[datetime] = None
    created_by_name:  Optional[str]      = None
    created_at:       Optional[datetime] = None
    updated_at:       Optional[datetime] = None
    ack_count:        int                = 0
    total_recipients: int                = 0

    # Key employee-specific fields
    acknowledged: bool               = False
    acked_at:     Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── ACKNOWLEDGE RESPONSE ─────────────────────────────────────────
class AcknowledgeOut(BaseModel):
    notice_id:   int
    employee_id: int
    acked_at:    datetime

    model_config = {"from_attributes": True}
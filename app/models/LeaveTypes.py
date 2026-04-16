from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, JSON
from sqlalchemy.sql import func
from .base import Base


class LeaveType(Base):
    __tablename__ = "leave_types"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String, nullable=False, unique=True)  # e.g. Casual, Sick, Annual
    code = Column(String, nullable=True, unique=True)   # e.g. CL, SL, AL
    description = Column(String, nullable=True)

    # Leave rules
    days_per_year = Column(Float, nullable=False, default=0)  # allocation per cycle
    carry_forward = Column(Boolean, default=False)            # can carry to next cycle
    max_carry_forward = Column(Float, nullable=True)          # limit if carry_forward = True

    # Restrictions
    allow_negative_balance = Column(Boolean, default=False)

    # Gender / special applicability (optional)
    gender_specific = Column(String, nullable=True)  # male, female, other (e.g. maternity)

    # Reset / cycle config
    reset_month = Column(Integer, nullable=True)  # 1–12 (Jan–Dec)

    # Status
    is_active = Column(Boolean, default=True)

    is_paid = Column(Boolean, default=True)
    requires_document = Column(Boolean, default=False)  # e.g. medical certificate
    min_days = Column(Float, nullable=True)
    max_days_per_request = Column(Float, nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    extradata = Column(JSON, nullable=True)  # for any future extensibility
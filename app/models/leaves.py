
from datetime import datetime
from .base import Base 
from sqlalchemy import (
    Column, String, Boolean, Integer, Date, DateTime,
    ForeignKey, Text, Enum as SAEnum, func, Index
)
from sqlalchemy.orm import relationship
import enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GenderSpecific(str, enum.Enum):
    ALL = "ALL"
    MALE = "MALE"
    FEMALE = "FEMALE"


class LeaveStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class LeavesCycle(Base):
    __tablename__ = "leaves_cycles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    leave_types = relationship(
        "LeaveType", back_populates="cycle", cascade="all, delete-orphan"
    )
    transactions = relationship("LeaveTransaction", back_populates="cycle")


class LeaveType(Base):
    __tablename__ = "leave_types"

    id = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, ForeignKey("leaves_cycles.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(120), nullable=False)
    gender_specific = Column(SAEnum(GenderSpecific), default=GenderSpecific.ALL)
    is_paid = Column(Boolean, default=True)

    min_days = Column(Integer, default=1)
    max_per_use = Column(Integer, default=30)
    total_per_cycle = Column(Integer, default=0)

    requires_document = Column(Boolean, default=False)
    document_description = Column(Text, nullable=True)
    allowed_file_types = Column(String(255), default="pdf,jpg,png,doc,docx")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cycle = relationship("LeavesCycle", back_populates="leave_types")
    transactions = relationship("LeaveTransaction", back_populates="leave_type")


class LeaveTransaction(Base):
    __tablename__ = "leave_transactions"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id", ondelete="RESTRICT"), nullable=False)
    cycle_id = Column(Integer, ForeignKey("leaves_cycles.id", ondelete="RESTRICT"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    requested_days = Column(Integer, nullable=False)

    status = Column(SAEnum(LeaveStatus), default=LeaveStatus.PENDING, index=True)

    employee_note = Column(Text)
    hr_note = Column(Text)

    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True))

    employee = relationship("Employee", foreign_keys=[employee_id])
    reviewer = relationship("Employee", foreign_keys=[reviewed_by])
    leave_type = relationship("LeaveType", back_populates="transactions")
    cycle = relationship("LeavesCycle", back_populates="transactions")
    attachments = relationship(
        "LeaveAttachment", back_populates="transaction", cascade="all, delete-orphan"
    )


class LeaveAttachment(Base):
    __tablename__ = "leave_attachments"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("leave_transactions.id", ondelete="CASCADE"), nullable=False)

    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))
    file_extension = Column(String(20))
    description = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("LeaveTransaction", back_populates="attachments")
    uploader = relationship("Employee")


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

Index("idx_leave_employee", LeaveTransaction.employee_id)
Index("idx_leave_status", LeaveTransaction.status)
Index("idx_leave_type", LeaveTransaction.leave_type_id)
Index("idx_leave_cycle", LeaveTransaction.cycle_id)
Index("idx_leave_dates", LeaveTransaction.start_date, LeaveTransaction.end_date)
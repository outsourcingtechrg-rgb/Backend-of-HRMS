from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Enum as SqlEnum,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base

class LeaveStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class LeaveCycle(Base):
    __tablename__ = "leave_cycles"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(50), nullable=False)  # e.g. "Jan-Dec", "Sep-Aug"

    start_month = Column(Integer, nullable=False)  # 1–12
    start_day = Column(Integer, default=1)

    end_month = Column(Integer, nullable=False)
    end_day = Column(Integer, default=31)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    leave_types = relationship("LeaveType", back_populates="leave_cycle")
    balances = relationship("LeaveBalance", back_populates="leave_cycle")


class LeaveType(Base):
    __tablename__ = "leave_types"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(50), unique=True, nullable=False)

    is_paid = Column(Boolean, default=True)

    max_per_cycle = Column(Float, default=0)

    carry_forward = Column(Boolean, default=False)
    max_carry_forward = Column(Float, default=0)

    leave_cycle_id = Column(ForeignKey("leave_cycles.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    leave_cycle = relationship("LeaveCycle", back_populates="leave_types")
    balances = relationship("LeaveBalance", back_populates="leave_type")
    requests = relationship("LeaveRequest", back_populates="leave_type")


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(ForeignKey("employees.id"), nullable=False)
    leave_type_id = Column(ForeignKey("leave_types.id"), nullable=False)
    leave_cycle_id = Column(ForeignKey("leave_cycles.id"), nullable=False)

    cycle_start_date = Column(Date, nullable=False)
    cycle_end_date = Column(Date, nullable=False)

    allocated = Column(Float, default=0)
    used = Column(Float, default=0)
    pending = Column(Float, default=0)
    carry_forward = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "leave_type_id",
            "cycle_start_date",
            name="uq_employee_leave_cycle",
        ),
    )

    # relationships
    leave_type = relationship("LeaveType", back_populates="balances")
    leave_cycle = relationship("LeaveCycle", back_populates="balances")

    @property
    def remaining(self):
        return self.allocated + self.carry_forward - self.used - self.pending
    
class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(ForeignKey("employees.id"), nullable=False)
    leave_type_id = Column(ForeignKey("leave_types.id"), nullable=False)
    leave_cycle_id = Column(ForeignKey("leave_cycles.id"), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    days = Column(Float, nullable=False)

    is_half_day = Column(Boolean, default=False)

    reason = Column(Text)

    status = Column(SqlEnum(LeaveStatusEnum), default=LeaveStatusEnum.pending)

    approved_by = Column(ForeignKey("employees.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    employee = relationship("Employee", back_populates="leave_requests", foreign_keys=[employee_id])
    approver = relationship("Employee", foreign_keys=[approved_by], overlaps="approved_leaves")
    leave_type = relationship("LeaveType", back_populates="requests")

class LeaveAuditLog(Base):
    __tablename__ = "leave_audit_logs"

    id = Column(Integer, primary_key=True)

    leave_request_id = Column(ForeignKey("leave_requests.id"), nullable=False)

    action = Column(String(50))  # applied, approved, rejected, cancelled

    performed_by = Column(ForeignKey("employees.id"))

    old_status = Column(String(20))
    new_status = Column(String(20))

    timestamp = Column(DateTime, default=datetime.utcnow)
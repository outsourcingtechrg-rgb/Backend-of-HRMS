from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class LeaveAllocation(Base):
    __tablename__ = "leave_allocations"

    id = Column(Integer, primary_key=True)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False, index=True)

    year = Column(Integer, nullable=False, index=True)

    allocated_days = Column(Float, default=0)
    used_days = Column(Float, default=0)
    carried_forward = Column(Float, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_allocation"),
    )

    # relations
    employee = relationship("Employee")
    leave_type = relationship("LeaveType")
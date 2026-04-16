from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class LeaveTransaction(Base):
    __tablename__ = "leave_transactions"

    id = Column(Integer, primary_key=True)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False, index=True)

    leave_request_id = Column(Integer, ForeignKey("leave_requests.id"), nullable=True)

    days = Column(Float, nullable=False)

    type = Column(String, nullable=False)
    # allocation, carry_forward, deduction, reversal, adjustment

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relations
    employee = relationship("Employee")
    leave_type = relationship("LeaveType")
    leave_request = relationship("LeaveRequest")
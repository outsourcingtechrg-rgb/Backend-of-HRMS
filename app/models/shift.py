from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    saturday_on = Column(Boolean, nullable=False, default=False)
    shift_start_timing = Column(Time, nullable=False)
    shift_end_timing = Column(Time, nullable=False)
    shift_late_on = Column(Time, nullable=True)
    total_hours = Column(Time, nullable=False)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    allow_remote = Column(Boolean, nullable=False, default=False)

    employees = relationship("Employee", back_populates="shift")

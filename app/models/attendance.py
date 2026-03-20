import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    Integer,
    JSON,
    Numeric,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class AttendanceModeEnum(str, enum.Enum):
    onsite = "onsite"
    remote = "remote"


class Attendance(Base):
    __tablename__ = "attendance"

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "attendance_date",
            "attendance_time",
            name="uq_employee_attendance_time",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(Integer, nullable=False, index=True)

    employee_name = Column(String(100), nullable=True)

    attendance_date = Column(Date, nullable=False)
    attendance_time = Column(Time, nullable=False)

    punch = Column(Boolean, nullable=False)

    attendance_mode = Column(
        SQLEnum(AttendanceModeEnum, name="attendance_mode_enum"),
        nullable=False,
        default=AttendanceModeEnum.onsite,
    )

#   if remote attendance:
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    ip_address = Column(String(255), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    synced_at = Column(DateTime, nullable=True)

    extra_data = Column(JSON, nullable=True)
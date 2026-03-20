from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from .base import Base


class AttendanceSync(Base):
    __tablename__ = "attendance_sync"

    id = Column(Integer, primary_key=True, index=True)
    device_ip = Column(String(255), unique=True, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    sync_interval_minutes = Column(Integer, nullable=False, default=10)
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now()) 
    
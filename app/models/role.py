from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    employees = relationship("Employee", back_populates="role")

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    department = Column(String(255), nullable=False)

    head_id = Column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    extra_data = Column(JSON, nullable=True)

    head = relationship(
        "Employee",
        foreign_keys=[head_id],
        primaryjoin="Department.head_id == Employee.id",
        viewonly=True,
    )

    employees = relationship(
        "Employee",
        back_populates="department",
        foreign_keys="Employee.department_id",
    )

# app/models/login_account.py
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class LoginAccount(Base):
    __tablename__ = "login_accounts"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    force_password_change = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )

    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    employee = relationship("Employee", back_populates="account")

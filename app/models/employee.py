import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class EmployeeStatusEnum(str, enum.Enum):
    inactive = "inactive"
    active = "active"
    resigned = "resigned"
    terminated = "terminated"


class Employee(Base):
    __tablename__ = "employees"
 
    # ────────────── Core Fields ──────────────
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, unique=True, nullable=True, index=True)
    f_name = Column(String(255), nullable=False)
    l_name = Column(String(255), nullable=False)
    image = Column(String(255), nullable=True)
    cell = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    gender = Column(String(50), nullable=False)

    designation = Column(String(255), nullable=True)
    join_date = Column(Date, nullable=False)

    employment_status = Column(
        SQLEnum(EmployeeStatusEnum, name="employment_status_enum"),
        nullable=False,
        default=EmployeeStatusEnum.active,
        index=True,
    )

    # ────────────── Relations (FKs) ──────────────
    role_id = Column(
        Integer,
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    manager_id = Column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    shift_id = Column(
        Integer,
        ForeignKey("shifts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
 
    # ────────────── Remote & Extensibility ──────────────
    is_remote = Column(Boolean, nullable=False, default=False)
    extra_data = Column(JSON, nullable=True)

    # ────────────── Audit Fields ──────────────
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    is_deleted = Column(Boolean, nullable=False, default=False)

    # ────────────── ORM Relationships ──────────────
    role = relationship("Role", back_populates="employees")

    department = relationship(
        "Department",
        back_populates="employees",
        foreign_keys=[department_id],
    )

    shift = relationship("Shift", back_populates="employees")

    # Manager ↔ Team
    manager = relationship(
        "Employee",
        remote_side=[id],
        back_populates="team_members",
        foreign_keys=[manager_id],
    )

    team_members = relationship(
        "Employee",
        back_populates="manager",
        foreign_keys=[manager_id],
    )

    account = relationship(
    "LoginAccount",
    back_populates="employee",
    uselist=False,
    )

    # # # Attendance
    # attendances = relationship(
    #     "Attendance",
    #     back_populates="employee",
    #     cascade="all, delete-orphan",
    # )

    # # Leave
    # leave_applications = relationship(
    #     "LeaveApplication",
    #     back_populates="employee",
    #     foreign_keys="LeaveApplication.employee_id",
    # )

    # approved_leaves = relationship(
    #     "LeaveApplication",
    #     back_populates="approver",
    #     foreign_keys="LeaveApplication.approved_by",
    # )

    # # KPI
    # kpis = relationship(
    #     "EmployeeKPI",
    #     back_populates="employee",
    #     foreign_keys="EmployeeKPI.employee_id",
    # )

    # reviewed_kpis = relationship(
    #     "EmployeeKPI",
    #     back_populates="reviewer",
    #     foreign_keys="EmployeeKPI.reviewed_by",
    # )

    # # Training
    # trainings_created = relationship(
    #     "Training",
    #     back_populates="creator",
    #     foreign_keys="Training.created_by",
    # )

    # employee_trainings = relationship(
    #     "EmployeeTraining",
    #     back_populates="employee",
    # )

    # # Policies
    # policies_created = relationship(
    #     "Policy",
    #     back_populates="creator",
    #     foreign_keys="Policy.created_by",
    # )

    # policy_acknowledgements = relationship(
    #     "PolicyAcknowledgement",
    #     back_populates="employee",
    # )

    # # Notices
    # notices_posted = relationship(
    #     "Notice",
    #     back_populates="poster",
    #     foreign_keys="Notice.posted_by",
    # )

    # notice_acknowledgements = relationship(
    #     "NoticeAcknowledgement",
    #     back_populates="employee",
    # )

    # # Reports
    # reports_generated = relationship(
    #     "Report",
    #     back_populates="generator",
    #     foreign_keys="Report.generated_by",
    # )

    # # Logs
    # logs = relationship(
    #     "Log",
    #     back_populates="employee",
    #     cascade="all, delete-orphan",
    # )

    # # Account (1–1, owned by Account table)
    # account = relationship(
    #     "Account",
    #     back_populates="employee",
    #     uselist=False,
    # )

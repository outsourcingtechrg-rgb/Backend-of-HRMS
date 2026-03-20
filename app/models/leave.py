# import enum

# from sqlalchemy import Column, Date, DateTime, Enum as SQLEnum, ForeignKey, Integer, JSON, String, Boolean
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from .base import Base


# class LeaveApplicationStatusEnum(str, enum.Enum):
#     pending = "pending"
#     approved = "approved"
#     rejected = "rejected"


# class LeaveType(Base):
#     __tablename__ = "leave_types"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(255), nullable=False)
#     max_days = Column(Integer, nullable=False)
#     paid = Column(Boolean, nullable=False, default=False)
#     extra_data = Column(JSON, nullable=True)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     leave_applications = relationship("LeaveApplication", back_populates="leave_type")


# class LeaveApplication(Base):
#     __tablename__ = "leave_applications"

#     id = Column(Integer, primary_key=True, index=True)
#     employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
#     start_date = Column(Date, nullable=False)
#     end_date = Column(Date, nullable=False)
#     reason = Column(String(1000), nullable=False)
#     status = Column(
#         SQLEnum(LeaveApplicationStatusEnum, name="leave_application_status_enum"),
#         nullable=False,
#         default=LeaveApplicationStatusEnum.pending,
#     )
#     approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())
#     extra_data = Column(JSON, nullable=True)

#     employee = relationship(
#         "Employee",
#         back_populates="leave_applications",
#         foreign_keys=[employee_id],
#     )
#     approver = relationship(
#         "Employee",
#         back_populates="approved_leaves",
#         foreign_keys=[approved_by],
#     )
#     leave_type = relationship("LeaveType", back_populates="leave_applications")

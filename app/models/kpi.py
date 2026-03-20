# from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from .base import Base


# class EmployeeKPI(Base):
#     __tablename__ = "employee_kpis"

#     id = Column(Integer, primary_key=True, index=True)
#     employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     kpi_name = Column(String(255), nullable=False)
#     score = Column(Numeric(10, 2), nullable=False)
#     reviewed_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     review_date = Column(Date, nullable=False)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())
#     extra_data = Column(JSON, nullable=True)

#     employee = relationship("Employee", back_populates="kpis", foreign_keys=[employee_id])
#     reviewer = relationship("Employee", back_populates="reviewed_kpis", foreign_keys=[reviewed_by])

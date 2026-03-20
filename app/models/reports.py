# from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from .base import Base


# class Report(Base):
#     __tablename__ = "reports"

#     id = Column(Integer, primary_key=True, index=True)
#     report_type = Column(String(255), nullable=False)
#     generated_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     generated_at = Column(DateTime, nullable=False)
#     extra_data = Column(JSON, nullable=True)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     generator = relationship("Employee", back_populates="reports_generated", foreign_keys=[generated_by])

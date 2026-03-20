# from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Boolean
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from .base import Base

# class Training(Base):
#     __tablename__ = "training"

#     id = Column(Integer, primary_key=True, index=True)
#     title = Column(String(255), nullable=False)
#     category = Column(String(255), nullable=False)
#     description = Column(String(2000), nullable=True)
#     effective_date = Column(Date, nullable=False)
#     last_updated = Column(Date, nullable=False)
#     version = Column(Numeric(10, 2), nullable=False)
#     mandatory_reading = Column(Boolean, nullable=False, default=False)
#     created_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     extra_data = Column(JSON, nullable=True)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     creator = relationship("Employee", back_populates="trainings_created", foreign_keys=[created_by])
#     employee_trainings = relationship("EmployeeTraining", back_populates="training")


# class EmployeeTraining(Base):
#     __tablename__ = "employee_training"

#     id = Column(Integer, primary_key=True, index=True)
#     employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     training_id = Column(Integer, ForeignKey("training.id"), nullable=False)
#     status = Column(String(50), nullable=False)
#     completion_date = Column(Date, nullable=True)
#     extra_data = Column(JSON, nullable=True)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     employee = relationship("Employee", back_populates="employee_trainings")
#     training = relationship("Training", back_populates="employee_trainings")

# from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from .base import Base


# class Log(Base):
#     __tablename__ = "logs"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column("user", Integer, ForeignKey("employees.id"), nullable=False)
#     task = Column(String(2000), nullable=False)
#     extra_data = Column(JSON, nullable=True)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     employee = relationship("Employee", back_populates="logs", foreign_keys=[user_id])

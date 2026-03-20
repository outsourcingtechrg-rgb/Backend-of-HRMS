# from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from .base import Base


# class Account(Base):
#     __tablename__ = "accounts"

#     id = Column(Integer, primary_key=True, index=True)
#     employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     account_holder = Column(String(255), nullable=False)
#     account_number = Column(String(255), nullable=False)
#     account_bank = Column(String(255), nullable=False)
#     extra_data = Column(JSON, nullable=True)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     employee = relationship(
#         "Employee",
#         foreign_keys=[employee_id],
#         back_populates="account",
#         uselist=False,
#     )

# from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Date, Boolean
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from .base import Base


# class PolicyType(Base):
#     __tablename__ = "policy_types"

#     id = Column(Integer, primary_key=True, index=True)
#     type_of_policy = Column(String(255), nullable=False)
#     extra_data = Column(JSON, nullable=True)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     policies = relationship("Policy", back_populates="policy_type")


# class Policy(Base):
#     __tablename__ = "policies"

#     id = Column(Integer, primary_key=True, index=True)
#     policy_type_id = Column(Integer, ForeignKey("policy_types.id"), nullable=False)
#     title = Column(String(255), nullable=False)
#     document_url = Column(String(500), nullable=False)
#     version = Column(String(50), nullable=False)
#     effective_date = Column(Date, nullable=False)
#     extra_data = Column(JSON, nullable=True)
#     created_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     policy_type = relationship("PolicyType", back_populates="policies")
#     creator = relationship("Employee", back_populates="policies_created", foreign_keys=[created_by])
#     acknowledgements = relationship("PolicyAcknowledgement", back_populates="policy")


# class PolicyAcknowledgement(Base):
#     __tablename__ = "policy_acknowledgements"

#     id = Column(Integer, primary_key=True, index=True)
#     policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
#     employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     acknowledged = Column(Boolean, nullable=False, default=False)
#     extra_data = Column(JSON, nullable=True)
#     acknowledged_at = Column(DateTime, nullable=True)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     policy = relationship("Policy", back_populates="acknowledgements")
#     employee = relationship("Employee", back_populates="policy_acknowledgements")

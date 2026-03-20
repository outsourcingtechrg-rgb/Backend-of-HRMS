# import enum

# from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, JSON, String
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from .base import Base


# class NoticeTypeEnum(str, enum.Enum):
#     Important = "Important"
#     Normal = "Normal"


# class Notice(Base):
#     __tablename__ = "notices"

#     id = Column(Integer, primary_key=True, index=True)
#     title = Column(String(255), nullable=False)
#     content = Column(String(4000), nullable=False)
#     type = Column(
#         SQLEnum(NoticeTypeEnum, name="notice_type_enum"),
#         nullable=False,
#         default=NoticeTypeEnum.Normal,
#     )
#     posted_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     posted_date = Column(DateTime, nullable=False)
#     is_pinned = Column(Boolean, nullable=False, default=False)
#     extra_data = Column(JSON, nullable=True)
#     acknowledgement_required = Column(Boolean, nullable=False, default=False)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     poster = relationship("Employee", back_populates="notices_posted", foreign_keys=[posted_by])
#     acknowledgements = relationship("NoticeAcknowledgement", back_populates="notice")


# class NoticeAcknowledgement(Base):
#     __tablename__ = "notice_acknowledgements"

#     id = Column(Integer, primary_key=True, index=True)
#     notice_id = Column(Integer, ForeignKey("notice.id"), nullable=False)
#     employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     acknowledged = Column(Boolean, nullable=False, default=False)
#     acknowledged_at = Column(DateTime, nullable=True)
#     extra_data = Column(JSON, nullable=True)
#     created_at = Column(DateTime, nullable=False, server_default=func.now())

#     notice = relationship("Notice", back_populates="acknowledgements")
#     employee = relationship("Employee", back_populates="notice_acknowledgements")

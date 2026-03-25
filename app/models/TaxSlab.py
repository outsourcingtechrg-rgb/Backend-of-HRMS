from sqlalchemy import DECIMAL, Boolean, Column, DateTime, Integer, String, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base

class TaxSlab(Base):
    __tablename__ = "tax_slabs"

    id = Column(Integer, primary_key=True, index=True)

    min_income = Column(DECIMAL(12, 2), nullable=False)  # inclusive
    max_income = Column(DECIMAL(12, 2), nullable=True)   # null = no upper limit

    tax_rate = Column(DECIMAL(5, 2), nullable=True)      # percentage (e.g. 5.00)
    fixed_tax = Column(DECIMAL(12, 2), default=0)        # fixed amount

    description = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    
    extra_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
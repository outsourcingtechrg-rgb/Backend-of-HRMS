from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DepartmentBase(BaseModel):
    department: str
    extra_data: Optional[dict] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    department: Optional[str] = None
    head_id: Optional[int] = None
    extra_data: Optional[dict] = None


class DepartmentOut(DepartmentBase):
    id: int
    head_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

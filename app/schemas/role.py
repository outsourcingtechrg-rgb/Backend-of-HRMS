from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    name: str = Field(..., example="HR")
    level: int = Field(..., example=3)
    extra_data: Optional[dict] = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    extra_data: Optional[dict] = None


class RoleResponse(RoleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

from datetime import date, datetime, time
from typing import Optional
from pydantic import BaseModel, field_validator

from app.models.employee import EmployeeStatusEnum
 
 
class EmployeeBase(BaseModel):
    f_name: str
    l_name: str
    image: Optional[str] = None
    gender: str
    cell: str
    email: str  # Changed from EmailStr to str for placeholder emails
    designation: str
    join_date: date
    employee_id: int
    role_id: int
    department_id: int
    shift_id: int
    manager_id: Optional[int] = None

    is_remote: bool = False
    extra_data: Optional[dict] = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    f_name: Optional[str] = None
    l_name: Optional[str] = None
    image: Optional[str] = None
    gender: Optional[str] = None
    cell: Optional[str] = None
    email: Optional[str] = None  # Changed from EmailStr to str
    designation: Optional[str] = None
    join_date: Optional[date] = None
    employee_id: Optional[int] = None
    role_id: Optional[int] = None
    department_id: Optional[int] = None
    shift_id: Optional[int] = None
    manager_id: Optional[int] = None

    employment_status: Optional[EmployeeStatusEnum] = None
    is_remote: Optional[bool] = None
    extra_data: Optional[dict] = None


class EmployeeOut(EmployeeBase):
    id: int
    employment_status: EmployeeStatusEnum
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RoleReadSchema(BaseModel):
    """Minimal role schema for nested read"""
    id: int
    name: str
    level: int

    class Config:
        from_attributes = True


class DepartmentReadSchema(BaseModel):
    """Minimal department schema for nested read"""
    id: int
    department: str

    class Config:
        from_attributes = True


class ShiftReadSchema(BaseModel):
    """Minimal shift schema for nested read"""
    id: int
    name: str
    shift_start_timing: str
    shift_end_timing: str

    @field_validator('shift_start_timing', 'shift_end_timing', mode='before')
    @classmethod
    def convert_time_to_string(cls, v):
        """Convert time objects to HH:MM:SS strings"""
        if isinstance(v, time):
            return v.strftime('%H:%M:%S')
        return v

    class Config:
        from_attributes = True


class EmployeeRead(EmployeeOut):
    """Full employee read schema with relationships"""
    employee_id: Optional[int] = None
    role: Optional[RoleReadSchema] = None
    department: Optional[DepartmentReadSchema] = None
    shift: Optional[ShiftReadSchema] = None
    manager_id: Optional[int] = None

    class Config:
        from_attributes = True

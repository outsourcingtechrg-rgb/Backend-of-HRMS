from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.crud import employee as employee_crud
from app.models.employee import Employee
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeOut,
    EmployeeRead,
)
from app.schemas.role import RoleResponse

router = APIRouter()


def _handle_integrity_error(exc: IntegrityError) -> None:
    message = str(getattr(exc, "orig", exc)).lower()
    if "duplicate entry" in message and "email" in message:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or conflicting data",
    )


@router.post("/", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_in: EmployeeCreate,
    db: Session = Depends(get_db),
):
    try:
        return employee_crud.create_employee(db, employee_in)
    except IntegrityError as exc:
        _handle_integrity_error(exc)


@router.get("/", response_model=list[EmployeeRead])
def list_employees(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Get employees list.
    
    If the current user is a department head, only returns employees in their department.
    Otherwise, admin/other roles see all employees.
    """
    # Check if current user is a department head
    headed_dept_id = employee_crud.get_headed_department_id(db, current_user.id)
    
    if headed_dept_id is not None:
        # User is a department head - filter to their department only
        return employee_crud.get_employees(
            db,
            skip=skip,
            limit=limit,
            department_id=headed_dept_id
        )
    else:
        # User is not a department head - return all employees
        return employee_crud.get_employees(
            db,
            skip=skip,
            limit=limit
        )


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = employee_crud.get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.get("/{employee_id}/role", response_model=RoleResponse)
def get_employee_role(employee_id: int, db: Session = Depends(get_db)):
    """Get the role of an employee by employee ID"""
    employee = employee_crud.get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not employee.role:
        raise HTTPException(status_code=404, detail="Employee role not found")
    
    return employee.role


@router.put("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    employee_in: EmployeeUpdate,
    db: Session = Depends(get_db),
):
    employee = employee_crud.get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    try:
        return employee_crud.update_employee(db, employee, employee_in)
    except IntegrityError as exc:
        _handle_integrity_error(exc)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    hard_delete: bool = False,
    db: Session = Depends(get_db),
):
    """
    Delete an employee.
    
    Args:
    - employee_id: Employee ID to delete
    - hard_delete: If True, permanently delete from database. If False (default), soft delete (mark as deleted)
    
    Query params:
    - hard_delete=true  → Permanently remove from database
    - hard_delete=false → Soft delete (mark as deleted, keep in DB)
    """
    employee = employee_crud.get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if hard_delete:
        employee_crud.hard_delete_employee(db, employee)
    else:
        employee_crud.soft_delete_employee(db, employee)
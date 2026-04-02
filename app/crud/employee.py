from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from app.models.employee import Employee
from app.models.department import Department
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.models.LoginAccount import LoginAccount
from app.core.security import hash_password

DEFAULT_PASSWORD = "123@Qwe"

def create_employee(db: Session, employee_in: EmployeeCreate) -> Employee:
    try:
        # Create employee and linked login account in one transaction.
        employee = Employee(**employee_in.dict())
        db.add(employee)
        db.flush()  # get employee.id before creating LoginAccount

        login = LoginAccount(
            email=employee.email,
            password_hash=hash_password(DEFAULT_PASSWORD),
            employee_id=employee.id,
            is_active=True,
            force_password_change=True,
        )
        db.add(login)

        db.commit()
        db.refresh(employee)

        return employee

    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

def get_employee(db: Session, employee_id: int):
    return (
        db.query(Employee)
        .filter(
            Employee.id == employee_id,
            Employee.is_deleted == False
        )
        .first()
    )


def get_department_of_employee(db: Session, employee_id: int) -> Optional[int]:
    """Get the department ID of an employee."""
    employee = get_employee(db, employee_id)
    return employee.department_id if employee else None


def is_department_head(db: Session, employee_id: int) -> bool:
    """Check if an employee is a department head."""
    dept = db.query(Department).filter(Department.head_id == employee_id).first()
    return dept is not None


def get_headed_department_id(db: Session, employee_id: int) -> Optional[int]:
    """Get the department ID if the employee is a head, otherwise None."""
    dept = db.query(Department).filter(Department.head_id == employee_id).first()
    return dept.id if dept else None
 

def get_employees(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[int] = None,
):
    """
    Get employees, optionally filtered by department.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        department_id: If provided, only return employees in this department
    
    Returns:
        List of employees
    """
    query = db.query(Employee).filter(Employee.is_deleted == False)
    
    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)
    
    return query.offset(skip).limit(limit).all()


def update_employee(
    db: Session,
    employee: Employee,
    employee_in: EmployeeUpdate,
) -> Employee:
    data = employee_in.dict(exclude_unset=True)

    try:
        for field, value in data.items():
            setattr(employee, field, value)

        db.commit()
        db.refresh(employee)
        return employee
    except IntegrityError:
        db.rollback()
        raise


def soft_delete_employee(db: Session, employee: Employee):
    employee.is_deleted = True
    db.commit()


def hard_delete_employee(db: Session, employee: Employee):
    """Permanently delete employee from database."""
    db.delete(employee)
    db.commit() 
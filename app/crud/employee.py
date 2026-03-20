from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.employee import Employee
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
 

def get_employees(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(Employee)
        .filter(Employee.is_deleted == False)
        .offset(skip)
        .limit(limit)
        .all()
    )


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
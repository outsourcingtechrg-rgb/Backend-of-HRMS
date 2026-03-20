from sqlalchemy.orm import Session

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate


def create_department(db: Session, department_in: DepartmentCreate) -> Department:
    department = Department(**department_in.dict(), head_id=None)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def get_department(db: Session, department_id: int) -> Department | None:
    return db.query(Department).filter(Department.id == department_id).first()


def get_departments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Department).offset(skip).limit(limit).all()


def update_department(
    db: Session,
    department: Department,
    department_in: DepartmentUpdate,
) -> Department:
    data = department_in.dict(exclude_unset=True)

    for field, value in data.items():
        setattr(department, field, value)

    db.commit()
    db.refresh(department)
    return department


def delete_department(db: Session, department: Department):
    db.delete(department)
    db.commit()

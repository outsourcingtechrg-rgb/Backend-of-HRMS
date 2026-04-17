from sqlalchemy.orm import Session, joinedload

from app.models.employee import Employee
from app.models.shift import Shift
from app.schemas.shift import ShiftCreate, ShiftUpdate


def create_shift(db: Session, shift_in: ShiftCreate) -> Shift:
    shift = Shift(**shift_in.dict())
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


def get_shift(db: Session, shift_id: int) -> Shift | None:
    return db.query(Shift).filter(Shift.id == shift_id).first()


def get_shift_by_employee_id(db: Session, employee_id: int) -> Shift | None:
    employee = (
        db.query(Employee)
        .options(joinedload(Employee.shift))  # optimize query
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        return None

    return employee.shift


def get_shifts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Shift).offset(skip).limit(limit).all()


def update_shift(db: Session, shift: Shift, shift_in: ShiftUpdate) -> Shift:
    data = shift_in.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(shift, field, value)

    db.commit()
    db.refresh(shift)
    return shift


def delete_shift(db: Session, shift: Shift):
    db.delete(shift)
    db.commit()

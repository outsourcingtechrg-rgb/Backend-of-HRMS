from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import shift as shift_crud
from app.schemas.shift import ShiftCreate, ShiftUpdate, ShiftOut

router = APIRouter()


@router.post("/", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
def create_shift(shift_in: ShiftCreate, db: Session = Depends(get_db)):
    return shift_crud.create_shift(db, shift_in)


@router.get("/", response_model=list[ShiftOut])
def list_shifts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return shift_crud.get_shifts(db, skip=skip, limit=limit)


@router.get("/{shift_id}", response_model=ShiftOut)
def get_shift(shift_id: int, db: Session = Depends(get_db)):
    shift = shift_crud.get_shift(db, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


@router.get("/employee/{employee_id}", response_model=ShiftOut)
def get_shift_by_employee_id(employee_id: int, db: Session = Depends(get_db)):
    shift = shift_crud.get_shift_by_employee_id(db, employee_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


@router.put("/{shift_id}", response_model=ShiftOut)
def update_shift(
    shift_id: int,
    shift_in: ShiftUpdate,
    db: Session = Depends(get_db),
):
    shift = shift_crud.get_shift(db, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    return shift_crud.update_shift(db, shift, shift_in)


@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    shift = shift_crud.get_shift(db, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    shift_crud.delete_shift(db, shift)

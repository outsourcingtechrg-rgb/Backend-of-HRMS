from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import department as department_crud
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentOut,
)

router = APIRouter()


@router.post("/", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    dept_in: DepartmentCreate,
    db: Session = Depends(get_db),
):
    return department_crud.create_department(db, dept_in)


@router.get("/", response_model=list[DepartmentOut])
def list_departments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return department_crud.get_departments(db, skip, limit)


@router.get("/{department_id}", response_model=DepartmentOut)
def get_department(department_id: int, db: Session = Depends(get_db)):
    department = department_crud.get_department(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return department


@router.put("/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: int,
    dept_in: DepartmentUpdate,
    db: Session = Depends(get_db),
):
    department = department_crud.get_department(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    return department_crud.update_department(db, department, dept_in)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(department_id: int, db: Session = Depends(get_db)):
    department = department_crud.get_department(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    department_crud.delete_department(db, department)

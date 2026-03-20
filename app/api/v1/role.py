from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List 

from app.core.database import get_db
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse
from app.crud import role as role_crud

router = APIRouter()


@router.post("/", response_model=RoleResponse)
def create_role(role_in: RoleCreate, db: Session = Depends(get_db)):
    return role_crud.create_role(db, role_in)


@router.get("/", response_model=List[RoleResponse])
def list_roles(db: Session = Depends(get_db)):
    return role_crud.get_roles(db)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(role_id: int, db: Session = Depends(get_db)):
    return role_crud.get_role(db, role_id)


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, role_in: RoleUpdate, db: Session = Depends(get_db)):
    return role_crud.update_role(db, role_id, role_in)


@router.delete("/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    role_crud.delete_role(db, role_id)
    return {"message": "Role deleted successfully"}

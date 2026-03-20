from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate


def create_role(db: Session, role_in: RoleCreate) -> Role:
    existing = db.query(Role).filter(Role.name == role_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists",
        )

    role = Role(
        name=role_in.name,
        level=role_in.level,
        extra_data=role_in.extra_data,
    )

    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def get_role(db: Session, role_id: int) -> Role:
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


def get_roles(db: Session):
    return db.query(Role).order_by(Role.level.asc()).all()


def update_role(db: Session, role_id: int, role_in: RoleUpdate) -> Role:
    role = get_role(db, role_id)

    for field, value in role_in.dict(exclude_unset=True).items():
        setattr(role, field, value)

    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: int):
    role = get_role(db, role_id)

    # if role.employees:
    #     raise HTTPException(
    #         status_code=400,
    #         detail="Cannot delete role assigned to employees",
    #     )

    db.delete(role)
    db.commit()

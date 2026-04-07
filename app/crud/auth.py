from datetime import datetime
from http.client import HTTPException

from sqlalchemy.orm import Session

from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    RESET_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.LoginAccount import LoginAccount


def create_account(db: Session, email: str, password: str, employee_id=None):
    account = LoginAccount(
        email=email,
        password_hash=hash_password(password),
        employee_id=employee_id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account

def authenticate(db: Session, email: str, password: str):
    account = (
        db.query(LoginAccount)
        .filter(LoginAccount.email == email)
        .first()
    )

    if not account:
        return None

    if not verify_password(password, account.password_hash):
        return None

    if not account.is_active or account.is_locked:
        return None

    # 🔥 Get level from relationship
    employee = account.employee
    role = employee.role if employee else None
    level = role.level if role else 0  # default = 0

    payload = {
        "sub": str(account.id),
        "EPI": account.employee_id,
        "id": employee.employee_id if employee else None, 
        "level": level,
    }

    # 🔹 Force password change case
    if account.force_password_change:
        token = create_access_token(payload, ACCESS_TOKEN_EXPIRE_MINUTES)

        return {
            "access_token": token,
            "token_type": "bearer",
            "force_change": True,
        }

    # 🔹 Normal login
    account.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token(payload, ACCESS_TOKEN_EXPIRE_MINUTES)

    return {
        "access_token": token,
        "token_type": "bearer",
        "force_change": False,
    }

def generate_reset_token(db: Session, email: str):
    account = db.query(LoginAccount).filter(LoginAccount.email == email).first()
    if not account:
        return None

    return create_access_token(
        {"sub": str(account.id), "type": "reset"},
        RESET_TOKEN_EXPIRE_MINUTES,
    )


def reset_password(db: Session, account_id: int, new_password: str):
    account = db.get(LoginAccount, account_id)
    if not account:
        return None
    account.password_hash = hash_password(new_password)
    account.force_password_change = False
    account.is_locked = False
    db.commit()
    return account


def change_password(db: Session, user_id: int, new_password: str):
    
    user = db.query(LoginAccount).filter(LoginAccount.id == user_id).first()

    if not user or not user.is_active or user.is_locked:
        raise HTTPException(status_code=404, detail="User not found")
    if user.force_password_change == False:
        raise HTTPException(status_code=400, detail="Password change not required")

    user.password_hash = hash_password(new_password)
    user.force_password_change = False

    db.commit()
    return user

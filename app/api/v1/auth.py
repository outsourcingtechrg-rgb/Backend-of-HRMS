# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import jwt, JWTError
import os
from app.schemas.auth import (
    ChangePasswordSchema,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.crud import auth as auth_crud
from app.core.security import SECRET_KEY, ALGORITHM
from app.core.database import get_db
from fastapi import BackgroundTasks
from app.core.email_sender import send_email
router = APIRouter()



@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = auth_crud.authenticate(db, data.email, data.password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    return result


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    token = auth_crud.generate_reset_token(db, data.email)

    # Always return same message (security)
    if not token:
        return {"message": "If email exists, reset link sent"}

    # ✅ Create reset link
    reset_link = f"{os.getenv('FRONTEND_URL')}/reset-password?token={token}"

    # ✅ Email content
    subject = "Password Reset Request of HRMS"
    body = f"""
    Hello,

    You requested a password reset.

    Click the link below to reset your password:
    {reset_link}

    If you did not request this, ignore this email.

    This link will expire soon.
    """

    # ✅ Send in background
    background_tasks.add_task(
        send_email,
        data.email,
        subject,
        body
    )

    return {"message": "Password reset link sent"}

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Invalid token type")
        account_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")

    updated = auth_crud.reset_password(db, account_id, data.new_password)
    if not updated:
        raise HTTPException(status_code=404, detail="Account not found")

    return {"message": "Password updated successfully"}

@router.post("/change-password")
def change_user_password(
    data: ChangePasswordSchema,
    db: Session = Depends(get_db)
):
    auth_crud.change_password(db, data.user_id, data.new_password)
    return {"message": "Password updated successfully"}
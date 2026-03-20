# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordSchema(BaseModel):
    user_id: int
    new_password: str = Field(min_length=8)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class LoginAccountCreate(BaseModel):
    email: EmailStr
    password: str
    employee_id: Optional[int] = None
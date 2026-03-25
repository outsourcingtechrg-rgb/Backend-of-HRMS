from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.employee import Employee
from app.models.LoginAccount import LoginAccount as auth
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

SECRET_KEY = "CHANGE_THIS"  # move to .env later
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
RESET_TOKEN_EXPIRE_MINUTES = 15

BCRYPT_MAX_LENGTH = 72  # 🔴 critical
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ────────────── Password Helpers ──────────────
def hash_password(password: str) -> str:
    # bcrypt safety
    password = password[:BCRYPT_MAX_LENGTH]
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    password = password[:BCRYPT_MAX_LENGTH]
    return pwd_context.verify(password, hashed)


# ────────────── JWT Helpers ──────────────
def create_access_token(data: dict, expires_minutes: int):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        account_id = int(payload.get("sub"))

    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    account = db.query(auth).filter(auth.id == account_id).first()

    if not account or not account.employee:
        raise credentials_exception

    return account.employee  # or return account if needed
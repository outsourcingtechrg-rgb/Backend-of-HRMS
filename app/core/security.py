from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

SECRET_KEY = "CHANGE_THIS"  # move to .env later
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
RESET_TOKEN_EXPIRE_MINUTES = 15

BCRYPT_MAX_LENGTH = 72  # 🔴 critical


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

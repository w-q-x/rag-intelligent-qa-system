import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Request

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", uuid.uuid4().hex)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password[:72], hashed_password)


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def get_current_user(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = decode_token(token)
        if payload:
            return payload.get("sub", "anonymous")
    return "anonymous"


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "get_current_user",
    "SECRET_KEY",
]

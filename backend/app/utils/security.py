# LogRaven — Security Utilities
#
# PURPOSE:
#   JWT token creation/validation and bcrypt password hashing.
#   Used by auth_service.py and dependencies.py.
#
# FUNCTIONS:
#   hash_password(plain: str) -> str
#     bcrypt hash with cost factor 12 (~250ms per hash)
#
#   verify_password(plain: str, hashed: str) -> bool
#     Compare plain text to bcrypt hash
#
#   create_access_token(user_id: str, tier: str) -> str
#     JWT with 15-minute expiry, contains user_id and tier claims
#
#   create_refresh_token(user_id: str) -> str
#     JWT with 7-day expiry, contains only user_id
#
#   decode_token(token: str) -> dict
#     Validates signature and expiry, returns claims dict
#     Raises TokenExpiredError or InvalidTokenError on failure
#
# TODO Month 1 Week 1: Implement this file.

from passlib.context import CryptContext
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-prod")
ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, tier: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15)))
    payload = {"sub": user_id, "tier": tier, "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7)))
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    # TODO: Add proper error handling with custom exceptions
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

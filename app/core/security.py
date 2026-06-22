import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Union
import bcrypt
from jose import jwt
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for a plain password."""
    # Default bcrypt.hashpw uses $2b$ format, matching doctor password regex check constraint
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(subject: Union[str, Any], expires_delta: Union[timedelta, None] = None) -> str:
    """Generate JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Union[str, None]:
    """Decode JWT access token and return subject (doctor_id)."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.JWTError:
        return None


def generate_raw_token() -> str:
    """Generate a high-entropy raw URL-safe token."""
    return secrets.token_urlsafe(32)


def get_assessment_token_hash(raw_token: str) -> str:
    """
    Generate SHA-256 hash of patient's assessment URL token.
    Must output exactly 64 lowercase hex chars to pass database constraint.
    """
    return hashlib.sha256(f"{raw_token}{settings.JWT_SECRET_KEY}".encode()).hexdigest()


def generate_otp_code() -> str:
    """Generate a secure 6-digit numeric OTP code."""
    # Ensure it's secure by using secrets.randbelow
    return "".join(str(secrets.randbelow(10)) for _ in range(6))


def get_otp_hash(otp: str) -> str:
    """
    Generate SHA-256 hash of OTP code.
    Must output exactly 64 lowercase hex chars.
    """
    return hashlib.sha256(f"{otp}{settings.OTP_SECRET_KEY}".encode()).hexdigest()

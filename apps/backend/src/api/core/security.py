from datetime import datetime, timedelta, timezone
import secrets
from typing import Any
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from api.core.config import settings

# Initialize password hasher using OWASP-recommended Argon2id algorithm
password_hash = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    """Hash password using Argon2id algorithm."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create signed JWT access token with short-lived expiration and type claim."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify validity of JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def generate_refresh_token() -> str:
    """Generate high-entropy cryptographically secure random refresh token string."""
    return secrets.token_urlsafe(48)


def get_refresh_token_expiry() -> datetime:
    """Calculate expiration timestamp for a new refresh token."""
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

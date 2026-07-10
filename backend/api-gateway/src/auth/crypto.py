from datetime import datetime, timedelta

import bcrypt
import jwt

from ..config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against hashed Bcrypt password."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(data: dict) -> str:
    """Generates a signed JWT with expiration timestamp."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

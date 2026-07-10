from typing import List, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """FastAPI Dependency validating authorization header JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        role: str = payload.get("role")
        zone_scope: Optional[str] = payload.get("zone_scope")
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token claims")
        return {"username": username, "role": role, "zone_scope": zone_scope}
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class RoleChecker:
    """FastAPI Dependency checking role permissions."""

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Insufficient permissions for this action",
            )
        return current_user

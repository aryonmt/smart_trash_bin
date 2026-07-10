import logging

from fastapi import APIRouter, HTTPException

from ..auth.crypto import create_access_token, verify_password
from ..database import db_manager
from ..models.auth import LoginRequest, TokenResponse

logger = logging.getLogger("APIGateway.Routers.Auth")
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Verifies credentials and generates an authenticated JWT session."""
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT username, password_hash, role, zone_scope FROM users WHERE username = %s;",
                (req.username,),
            )
            user = cursor.fetchone()

            if not user or not verify_password(req.password, user["password_hash"]):
                raise HTTPException(
                    status_code=401, detail="Incorrect username or password"
                )

            token_data = {
                "sub": user["username"],
                "role": user["role"],
                "zone_scope": user["zone_scope"],
            }
            token = create_access_token(token_data)
            return {
                "access_token": token,
                "token_type": "bearer",
                "role": user["role"],
                "username": user["username"],
            }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Login process error: {e}")
        raise HTTPException(status_code=500, detail="Internal server login error")
    finally:
        db_manager.release_connection(conn)

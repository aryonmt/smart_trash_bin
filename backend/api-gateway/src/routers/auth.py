# backend/api-gateway/src/routers/auth.py
# -------------------------------------------------------------------------
# APIRouter - Authenticates user credentials with Redis-based Rate Limiter
# -------------------------------------------------------------------------

import logging

from fastapi import APIRouter, HTTPException, Request

from ..auth.crypto import create_access_token, verify_password
from ..database import db_manager
from ..models.auth import LoginRequest, TokenResponse
from ..redis_client import redis_client

logger = logging.getLogger("APIGateway.Routers.Auth")
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request):
    """Verifies credentials and generates an authenticated JWT session with Rate Limiting."""
    # 1. Redis-based Rate Limiting (Protects against Brute-Force attacks)
    client_ip = request.client.host
    rate_limit_key = f"login_attempts:{client_ip}"

    attempts = redis_client.get(rate_limit_key)
    if attempts and int(attempts) >= 5:
        logger.warning(
            f"[SECURITY ALERT] Blocked brute-force attempt from IP: {client_ip}"
        )
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Your IP has been temporarily locked for 15 minutes.",
        )

    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT username, password_hash, role, zone_scope FROM users WHERE username = %s;",
                (req.username,),
            )
            user = cursor.fetchone()

            if not user or not verify_password(req.password, user["password_hash"]):
                # Increment failed attempts and set 15 minutes (900 seconds) sliding expiration
                redis_client.incr(rate_limit_key)
                redis_client.expire(rate_limit_key, 900)

                raise HTTPException(
                    status_code=401, detail="Incorrect username or password"
                )

            # Successful login: Reset rate limit counters for this IP
            redis_client.delete(rate_limit_key)

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

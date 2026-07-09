# backend/api-gateway/main.py
# -------------------------------------------------------------------------
# API Gateway - Enhanced with JWT Authentication & Role-Based Access Control
# -------------------------------------------------------------------------

import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Optional

import bcrypt
import jwt
import psycopg2
import redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("APIGateway")

# Security Configurations
JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_jwt_key_2026_smart_waste")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Environment configurations
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://wastebin_app:securepassword@localhost:5432/wastebin"
)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

app = FastAPI(title="Smart Waste Bin IoT API Gateway")
security = HTTPBearer()

# backend/api-gateway/main.py (Modify CORS settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # FIXED: Wildcard (*) is now compatible because credentials are not passed via cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to TimescaleDB
db_conn = None
for attempt in range(1, 11):
    try:
        db_conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        db_conn.autocommit = True
        logger.info("API Gateway successfully connected to TimescaleDB.")
        break
    except Exception as e:
        logger.warning(f"Database connection attempt {attempt}/10 failed: {e}")
        time.sleep(3)
if not db_conn:
    exit(1)

try:
    with db_conn.cursor() as cursor:
        # Check if users table is populated
        cursor.execute("SELECT COUNT(*) FROM users;")
        count_record = cursor.fetchone()
        user_count = count_record["count"] if count_record else 0

        if user_count == 0:
            logger.info(
                "[STARTUP] No users found in database. Initializing default admin user..."
            )
            raw_password = "adminpassword2026"
            # Securely hash password using python-bcrypt inside the container
            hashed_password = bcrypt.hashpw(
                raw_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s);",
                ("admin", hashed_password, "admin"),
            )
            logger.info(
                "[STARTUP] Default admin user successfully registered with password hash."
            )
except Exception as e:
    logger.error(
        f"[STARTUP] Critical warning during users table auto-seeding verification: {e}"
    )


# Connect to Redis
redis_client = None
for attempt in range(1, 11):
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
        )
        redis_client.ping()
        logger.info("API Gateway connected to Redis.")
        break
    except Exception as e:
        logger.warning(f"Redis connection attempt {attempt}/10 failed: {e}")
        time.sleep(3)
if not redis_client:
    exit(1)


# --- Pydantic Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str


class BinCreateRequest(BaseModel):
    bin_id: str = Field(..., min_length=3)
    zone_id: str = Field(..., min_length=3)
    bin_depth_cm: float = Field(150.0, ge=100.0)
    label: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


class BinResponse(BaseModel):
    bin_id: str
    zone_id: str
    bin_depth_cm: float
    current_fill_pct: Optional[float] = None
    last_reading_at: Optional[datetime] = None
    last_emptied_at: Optional[datetime] = None
    status: str
    last_status_at: Optional[datetime] = None


class ReadingHistoryResponse(BaseModel):
    time: datetime
    distance_cm: float
    fill_percent: float
    emptied_this_cycle: bool


class AlertResponse(BaseModel):
    id: int
    bin_id: str
    alert_type: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class AcknowledgeRequest(BaseModel):
    operator_name: str


# --- Authentication Helpers ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Dependency to validate JWT and return payload containing user claims."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
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
    """Helper dependency to enforce Role-Based Access Control constraints."""

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Insufficient permissions for this action",
            )
        return current_user


# --- REST Endpoints ---


@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Verifies credentials and generates an authenticated JWT session."""
    try:
        with db_conn.cursor() as cursor:
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


@app.get("/api/bins", response_model=List[BinResponse])
def get_bins(user: dict = Depends(get_current_user)):
    """Retrieve operational bins. (Allowed: admin, operator, driver)"""
    try:
        with db_conn.cursor() as cursor:
            # If the logged-in user is a driver or scoped operator, filter results by their zone
            if user["role"] in ["operator", "driver"] and user["zone_scope"]:
                cursor.execute(
                    "SELECT bin_id, zone_id, bin_depth_cm, current_fill_pct, "
                    "last_reading_at, last_emptied_at, status, last_status_at FROM bins "
                    "WHERE zone_id = %s ORDER BY bin_id;",
                    (user["zone_scope"],),
                )
            else:
                cursor.execute(
                    "SELECT bin_id, zone_id, bin_depth_cm, current_fill_pct, "
                    "last_reading_at, last_emptied_at, status, last_status_at FROM bins ORDER BY bin_id;"
                )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching bins list: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")


@app.get("/api/bins/{bin_id}/history", response_model=List[ReadingHistoryResponse])
def get_bin_history(
    bin_id: str, limit: int = 30, user: dict = Depends(get_current_user)
):
    """Fetch sensory history. (Allowed: admin, operator, driver)"""
    try:
        with db_conn.cursor() as cursor:
            # Scoped security check: Drivers can only view history within their municipal boundary
            if user["role"] == "driver" and user["zone_scope"]:
                cursor.execute("SELECT zone_id FROM bins WHERE bin_id = %s;", (bin_id,))
                bin_record = cursor.fetchone()
                if not bin_record or bin_record["zone_id"] != user["zone_scope"]:
                    raise HTTPException(
                        status_code=403, detail="Access denied to this bin's history"
                    )

            cursor.execute(
                "SELECT time, distance_cm, fill_percent, emptied_this_cycle FROM readings "
                "WHERE bin_id = %s ORDER BY time DESC LIMIT %s;",
                (bin_id, limit),
            )
            return cursor.fetchall()
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching history for {bin_id}: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")


@app.get("/api/alerts", response_model=List[AlertResponse])
def get_alerts(
    status: str = "open", user: dict = Depends(RoleChecker(["admin", "operator"]))
):
    """Retrieve unresolved alerts. (Allowed: admin, operator)"""
    try:
        with db_conn.cursor() as cursor:
            if status == "open":
                cursor.execute(
                    "SELECT * FROM alerts WHERE resolved_at IS NULL ORDER BY triggered_at DESC;"
                )
            else:
                cursor.execute("SELECT * FROM alerts ORDER BY triggered_at DESC;")
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")


@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    req: AcknowledgeRequest,
    user: dict = Depends(RoleChecker(["admin", "operator"])),
):
    """Mark an alert as acknowledged. (Allowed: admin, operator)"""
    try:
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT id FROM alerts WHERE id = %s;", (alert_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Alert not found")

            cursor.execute(
                "UPDATE alerts SET acknowledged_by = %s WHERE id = %s;",
                (req.operator_name, alert_id),
            )
            return {
                "status": "success",
                "message": f"Alert {alert_id} acknowledged by {req.operator_name}.",
            }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Database update error")


@app.post("/api/bins/{bin_id}/empty")
def manual_empty_bin(
    bin_id: str, user: dict = Depends(RoleChecker(["admin", "operator"]))
):
    """Manually clear a bin. (Allowed: admin, operator)"""
    try:
        now_ts = datetime.utcnow()

        with db_conn.cursor() as cursor:
            cursor.execute(
                "SELECT bin_depth_cm FROM bins WHERE bin_id = %s;", (bin_id,)
            )
            record = cursor.fetchone()
            if not record:
                raise HTTPException(status_code=404, detail=f"Bin {bin_id} not found")

            bin_depth = record["bin_depth_cm"]

            cursor.execute(
                "UPDATE bins SET current_fill_pct = 0.0, last_emptied_at = %s, last_reading_at = %s WHERE bin_id = %s;",
                (now_ts, now_ts, bin_id),
            )

            cursor.execute(
                "UPDATE alerts SET resolved_at = %s WHERE bin_id = %s AND resolved_at IS NULL;",
                (now_ts, bin_id),
            )

            cursor.execute(
                "INSERT INTO readings (time, bin_id, distance_cm, fill_percent, is_confirmed, emptied_this_cycle) "
                "VALUES (%s, %s, %s, 0.0, True, True);",
                (now_ts, bin_id, bin_depth),
            )

        state_key = f"bin_state:{bin_id}"
        redis_client.delete(state_key)

        logger.warning(
            f"[MANUAL OVERRIDE] Bin {bin_id} manually cleared by administrator: {user['username']}."
        )
        return {
            "status": "success",
            "message": f"Bin {bin_id} manually cleared and Redis state reset.",
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error manually emptying bin {bin_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal manual empty error")


@app.post("/api/bins", status_code=201)
def create_bin(req: BinCreateRequest, user: dict = Depends(RoleChecker(["admin"]))):
    """Explicitly registers/provisions a new smart waste bin in the database."""
    try:
        now_ts = datetime.utcnow()
        with db_conn.cursor() as cursor:
            # Check if bin already exists
            cursor.execute("SELECT bin_id FROM bins WHERE bin_id = %s;", (req.bin_id,))
            if cursor.fetchone():
                raise HTTPException(
                    status_code=400, detail="Bin with this ID already registered"
                )

            cursor.execute(
                "INSERT INTO bins (bin_id, zone_id, bin_depth_cm, label, latitude, longitude, status, provisioned, last_status_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'unknown', TRUE, %s);",
                (
                    req.bin_id,
                    req.zone_id,
                    req.bin_depth_cm,
                    req.label,
                    req.latitude,
                    req.longitude,
                    now_ts,
                ),
            )
            logger.info(
                f"[PROVISIONING] Bin {req.bin_id} explicitly registered by admin user: {user['username']}."
            )
            return {
                "status": "success",
                "message": f"Bin {req.bin_id} successfully provisioned.",
            }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error provisioning bin: {e}")
        raise HTTPException(status_code=500, detail="Failed to register bin")

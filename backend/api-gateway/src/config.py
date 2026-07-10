# backend/api-gateway/src/config.py
# -------------------------------------------------------------------------
# Configuration module loading and validating environment variables
# -------------------------------------------------------------------------

import logging
import os

logger = logging.getLogger("APIGateway.Config")


class Settings:
    """Loads and validates configuration from environment variables."""

    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://wastebin_app:securepassword@localhost:5432/wastebin",
    )
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))


settings = Settings()

# Fail-Fast Guard: Force crash if JWT_SECRET is vulnerable or missing
if (
    not settings.JWT_SECRET
    or settings.JWT_SECRET == "super_secret_jwt_key_2026_smart_waste"
):
    logger.critical(
        "FATAL SECURITY THREAT: The JWT_SECRET environment variable is missing, "
        "empty, or configured with the vulnerable default value! Deployment halted."
    )
    raise RuntimeError(
        "Vulnerable or unconfigured JWT_SECRET detected. Server terminated."
    )

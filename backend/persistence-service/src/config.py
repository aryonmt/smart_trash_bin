# backend/persistence-service/src/config.py
# -------------------------------------------------------------------------
# Configuration module loading environment variables
# -------------------------------------------------------------------------

import os
import socket


class Settings:
    """Loads and validates configuration from environment variables."""

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://wastebin_app:securepassword@localhost:5432/wastebin",
    )

    STREAM_FILL_UPDATED: str = "bin-fill-updated"
    STREAM_STATUS: str = "device-status"

    GROUP_TELEMETRY: str = "persistence-telemetry-group"
    GROUP_STATUS: str = "persistence-status-group"

    # Dynamic Consumer Name: Append hostname to guarantee unique naming in replica sets
    CONSUMER_NAME: str = f"persistence-consumer-{socket.gethostname()}"


settings = Settings()

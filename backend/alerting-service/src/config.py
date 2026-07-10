# backend/alerting-service/src/config.py
# -------------------------------------------------------------------------
# Configuration module loading environment variables
# -------------------------------------------------------------------------

import os
import socket


class Settings:
    """Centralized configuration manager for the Alerting Service."""

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://wastebin_app:securepassword@localhost:5432/wastebin",
    )

    STREAM_FILL_UPDATED: str = "bin-fill-updated"
    GROUP_ALERTING: str = "alerting-telemetry-group"

    # Generate a unique consumer name dynamically per docker replica hostname
    CONSUMER_NAME: str = f"alerting-consumer-{socket.gethostname()}"


settings = Settings()

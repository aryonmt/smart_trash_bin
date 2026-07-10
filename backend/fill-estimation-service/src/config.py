# backend/fill-estimation-service/src/config.py
# -------------------------------------------------------------------------
# Configuration module loading and validating environment variables
# -------------------------------------------------------------------------

import os
import socket


class Settings:
    """Loads and validates configuration from environment variables."""

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))

    STREAM_TELEMETRY: str = "raw-telemetry"
    STREAM_FILL_UPDATED: str = "bin-fill-updated"
    CONSUMER_GROUP: str = "estimation-group"

    # Dynamic Consumer Name: Append hostname to guarantee unique naming in replica sets
    CONSUMER_NAME: str = f"estimator-consumer-{socket.gethostname()}"


settings = Settings()

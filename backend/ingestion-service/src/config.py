# backend/ingestion-service/src/config.py
# -------------------------------------------------------------------------
# Configuration module loading environment variables
# -------------------------------------------------------------------------

import os


class Settings:
    """Loads and validates configuration from environment variables."""

    MQTT_BROKER: str = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", 1883))
    MQTT_USER: str = os.getenv("MQTT_USER", "")
    MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD", "")

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))

    TELEMETRY_PATTERN: str = "wastebin/+/+/telemetry"
    STATUS_PATTERN: str = "wastebin/+/+/status"

    STREAM_TELEMETRY: str = "raw-telemetry"
    STREAM_STATUS: str = "device-status"


settings = Settings()

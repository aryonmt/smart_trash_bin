# backend/alerting-service/src/database.py
# -------------------------------------------------------------------------
# Thread-safe connection pool manager for TimescaleDB
# -------------------------------------------------------------------------

import logging
import time

from psycopg2.pool import ThreadedConnectionPool

from .config import settings

logger = logging.getLogger("AlertingService.Database")


class DatabaseManager:
    """Manages pool connection lifecycles for TimescaleDB."""

    def __init__(self):
        self._pool = None

    def initialize(self) -> None:
        """Initialize connection pool with robust connection retries."""
        for attempt in range(1, 11):
            try:
                # Thread-safe pool supporting min 1 and max 10 concurrent connections
                self._pool = ThreadedConnectionPool(
                    minconn=1, maxconn=10, dsn=settings.DATABASE_URL
                )
                logger.info("Successfully initialized TimescaleDB connection pool.")
                break
            except Exception as e:
                logger.warning(
                    f"Database connection pool attempt {attempt}/10 failed: {e}"
                )
                time.sleep(3)
        if not self._pool:
            logger.critical("Could not establish connection pool to database.")
            raise RuntimeError("Database pool initialization failed.")

    def get_connection(self):
        """Retrieve an active connection from the pool."""
        if not self._pool:
            self.initialize()
        return self._pool.getconn()

    def release_connection(self, conn) -> None:
        """Return used connection safely back to the pool."""
        if self._pool and conn:
            self._pool.putconn(conn)


db_manager = DatabaseManager()

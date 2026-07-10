# backend/api-gateway/src/database.py
# -------------------------------------------------------------------------
# Thread-safe database connection pool manager and startup seeder
# -------------------------------------------------------------------------

import logging
import time

import bcrypt
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from .config import settings

logger = logging.getLogger("APIGateway.Database")


class DatabaseManager:
    """Manages pool connection lifecycles for TimescaleDB and handles startup seeding."""

    def __init__(self):
        self._pool = None

    def initialize(self) -> None:
        """Initialize connection pool with robust connection retries."""
        for attempt in range(1, 11):
            try:
                self._pool = ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=settings.DATABASE_URL,
                    cursor_factory=RealDictCursor,
                )
                logger.info(
                    "Successfully connected to TimescaleDB and initialized pool."
                )
                break
            except Exception as e:
                logger.warning(
                    f"Database connection pool attempt {attempt}/10 failed: {e}"
                )
                time.sleep(3)
        if not self._pool:
            logger.critical("Could not establish connection pool to database.")
            raise RuntimeError("Database pool initialization failed.")

        # Verify and seed default admin user on startup
        self._seed_admin_user()

    def get_connection(self):
        """Retrieve an active connection from the pool."""
        if not self._pool:
            self.initialize()
        return self._pool.getconn()

    def release_connection(self, conn) -> None:
        """Return used connection safely back to the pool."""
        if self._pool and conn:
            self._pool.putconn(conn)

    def _seed_admin_user(self) -> None:
        """Seeds the default admin account safely on pool initialization."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM users;")
                count_record = cursor.fetchone()
                user_count = count_record["count"] if count_record else 0

                if user_count == 0:
                    logger.info(
                        "[STARTUP] No registered users detected. Seeding default master admin..."
                    )
                    raw_password = "secure_admin_master_pass_2026"
                    hashed_password = bcrypt.hashpw(
                        raw_password.encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8")

                    cursor.execute(
                        "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s);",
                        ("admin", hashed_password, "admin"),
                    )
                    logger.info(
                        "[STARTUP] Master administrator account successfully provisioned."
                    )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(
                f"[STARTUP] Critical warning during users table auto-seeding: {e}"
            )
        finally:
            self.release_connection(conn)


db_manager = DatabaseManager()

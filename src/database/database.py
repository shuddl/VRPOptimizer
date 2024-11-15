import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any, List
import json
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from tenacity import retry, stop_after_attempt, wait_fixed
from src.core.settings import Settings
from src.core.exceptions import VRPOptimizerError

Base = declarative_base()


class DatabaseError(VRPOptimizerError):
    """Database specific errors."""

    pass


class DatabaseConnection:
    """Manages asynchronous database connections and sessions."""

    _instance = None

    @classmethod
    async def get_instance(cls, settings: Settings):
        if cls._instance is None:
            cls._instance = cls(settings)
            await cls._instance.initialize()
        return cls._instance

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = None
        self._initialized = False  # Add this flag
        self.logger = logging.getLogger(__name__)

    @property
    def is_connected(self) -> bool:
        """Check if database is initialized and connected."""
        return self._initialized and self.engine is not None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
    async def initialize(self):
        """Initialize the asynchronous database engine and sessionmaker."""
        try:
            if not self.engine:
                # Configure engine based on database type
                if self.settings.DATABASE_URL.startswith('sqlite'):
                    # SQLite-specific configuration
                    self.engine = create_async_engine(
                        self.settings.DATABASE_URL,
                        echo=self.settings.DEBUG,
                    )
                else:
                    # Configuration for other databases (PostgreSQL, MySQL, etc.)
                    self.engine = create_async_engine(
                        self.settings.DATABASE_URL,
                        echo=self.settings.DEBUG,
                        pool_size=self.settings.DB_POOL_SIZE,
                        max_overflow=self.settings.DB_MAX_OVERFLOW,
                        pool_timeout=self.settings.DB_POOL_TIMEOUT,
                        pool_recycle=self.settings.DB_POOL_RECYCLE,
                    )
            
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self._initialized = True  # Set flag when initialization succeeds
            self.logger.info(f"Connected to database: {self.settings.DATABASE_URL}")
        except OperationalError as e:
            self._initialized = False
            self.logger.error(f"Database initialization error: {str(e)}")
            raise DatabaseError(f"Failed to initialize database: {str(e)}") from e

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide an asynchronous session."""
        async with self.SessionLocal() as session:
            yield session

    async def check_connection(self) -> bool:
        """Check if database connection is alive."""
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error(f"Database connection check failed: {str(e)}")
            return False

    async def get_cached_coordinates(
        self, location_key: str
    ) -> Optional[Dict[str, float]]:
        """Retrieve cached coordinates for a location."""
        async with self.get_session() as session:
            result = await session.execute(
                text(
                    "SELECT latitude, longitude FROM geocoding_cache WHERE location_key = :key"
                ),
                {"key": location_key},
            )
            row = result.fetchone()
            if row:
                return {"latitude": row.latitude, "longitude": row.longitude}
            return None

    async def cache_coordinates(
        self, location_key: str, latitude: float, longitude: float
    ):
        """Cache coordinates for a location."""
        async with self.get_session() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO geocoding_cache (location_key, latitude, longitude)
                    VALUES (:key, :lat, :lon)
                    ON CONFLICT(location_key) DO UPDATE SET
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        updated_at = CURRENT_TIMESTAMP
                """
                ),
                {"key": location_key, "lat": latitude, "lon": longitude},
            )
            await session.commit()

    async def save_solution(
        self, solution_data: Dict[str, Any], metrics: Optional[Dict] = None
    ):
        """Save optimization solution."""
        async with self.get_session() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO solutions (solution_data, metrics)
                    VALUES (:data, :metrics)
                """
                ),
                {
                    "data": json.dumps(solution_data),
                    "metrics": json.dumps(metrics) if metrics else None,
                },
            )
            await session.commit()

    async def get_recent_solutions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent solutions."""
        async with self.get_session() as session:
            result = await session.execute(
                text(
                    """
                    SELECT solution_data, metrics, created_at 
                    FROM solutions 
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """
                ),
                {"limit": limit},
            )
            rows = result.fetchall()
            return [
                {
                    "solution": json.loads(row.solution_data),
                    "metrics": json.loads(row.metrics) if row.metrics else None,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    async def set_cache(self, key: str, value: Any, expires_in: int):
        """Set cache value with expiration."""
        async with self.get_session() as session:
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            await session.execute(
                text(
                    """
                    INSERT INTO cache (key, value, expires_at)
                    VALUES (:key, :value, :expires_at)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        expires_at = excluded.expires_at
                """
                ),
                {"key": key, "value": json.dumps(value), "expires_at": expires_at},
            )
            await session.commit()

    async def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value if not expired."""
        async with self.get_session() as session:
            result = await session.execute(
                text(
                    """
                    SELECT value FROM cache 
                    WHERE key = :key AND expires_at > :now
                """
                ),
                {"key": key, "now": datetime.now()},
            )
            row = result.fetchone()
            if row:
                return json.loads(row.value)
            return None

    async def cleanup_expired_cache(self):
        """Remove expired cache entries."""
        async with self.get_session() as session:
            await session.execute(
                text("DELETE FROM cache WHERE expires_at <= :now"),
                {"now": datetime.now()},
            )
            await session.commit()

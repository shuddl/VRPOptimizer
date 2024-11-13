# src/database/database.py
import aiosqlite
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import logging
from contextlib import asynccontextmanager

from ..core.config import Settings
from ..core.exceptions import VRPOptimizerError

class DatabaseError(VRPOptimizerError):
    """Database specific errors."""
    pass

class DatabaseConnection:
    """Manages database connections."""
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
        self.logger = logging.getLogger(__name__)

    async def connect(self):
        """Establish database connection."""
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            await self.conn.execute('PRAGMA foreign_keys = ON')
            self.logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}")
            raise DatabaseError(f"Failed to connect to database: {str(e)}")

    async def disconnect(self):
        """Close database connection."""
        if self.conn:
            await self.conn.close()
            self.conn = None
            self.logger.info("Database connection closed")

    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        if not self.conn:
            raise DatabaseError("No database connection")
        
        try:
            await self.conn.execute('BEGIN TRANSACTION')
            yield self.conn
            await self.conn.commit()
        except Exception as e:
            await self.conn.rollback()
            raise DatabaseError(f"Transaction failed: {str(e)}")

class Database:
    """Main database interface."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db_path = Path(settings.database_path)
        self._connection = DatabaseConnection(self.db_path)
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize database and create necessary tables."""
        try:
            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to database
            await self._connection.connect()
            
            # Create tables
            await self._create_tables()
            
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise DatabaseError(f"Failed to initialize database: {str(e)}")

    async def _create_tables(self):
        """Create all required database tables."""
        async with self._connection.transaction() as conn:
            # Geocoding cache table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS geocoding_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location_key TEXT UNIQUE NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Solutions table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    solution_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metrics TEXT
                )
            ''')

            # Cache table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            ''')

    async def close(self):
        """Close database connection."""
        await self._connection.disconnect()

    # Geocoding cache methods
    async def get_cached_coordinates(self, location_key: str) -> Optional[Dict[str, float]]:
        """Retrieve cached coordinates for a location."""
        async with self._connection.transaction() as conn:
            cursor = await conn.execute(
                'SELECT latitude, longitude FROM geocoding_cache WHERE location_key = ?',
                (location_key,)
            )
            result = await cursor.fetchone()
            
            if result:
                return {
                    'latitude': result[0],
                    'longitude': result[1]
                }
            return None

    async def cache_coordinates(self, location_key: str, latitude: float, longitude: float):
        """Cache coordinates for a location."""
        async with self._connection.transaction() as conn:
            await conn.execute('''
                INSERT INTO geocoding_cache (location_key, latitude, longitude)
                VALUES (?, ?, ?)
                ON CONFLICT(location_key) DO UPDATE SET
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    updated_at = CURRENT_TIMESTAMP
            ''', (location_key, latitude, longitude))

    # Solution storage methods
    async def save_solution(self, solution_data: Dict[str, Any], metrics: Optional[Dict] = None):
        """Save optimization solution."""
        async with self._connection.transaction() as conn:
            await conn.execute('''
                INSERT INTO solutions (solution_data, metrics)
                VALUES (?, ?)
            ''', (json.dumps(solution_data), json.dumps(metrics) if metrics else None))

    async def get_recent_solutions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent solutions."""
        async with self._connection.transaction() as conn:
            cursor = await conn.execute('''
                SELECT solution_data, metrics, created_at 
                FROM solutions 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            results = await cursor.fetchall()
            return [
                {
                    'solution': json.loads(row[0]),
                    'metrics': json.loads(row[1]) if row[1] else None,
                    'created_at': row[2]
                }
                for row in results
            ]

    # General cache methods
    async def set_cache(self, key: str, value: Any, expires_in: int):
        """Set cache value with expiration."""
        async with self._connection.transaction() as conn:
            expires_at = datetime.now().timestamp() + expires_in
            value_json = json.dumps(value)
            
            await conn.execute('''
                INSERT INTO cache (key, value, expires_at)
                VALUES (?, ?, datetime(?))
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    expires_at = excluded.expires_at
            ''', (key, value_json, expires_at))

    async def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value if not expired."""
        async with self._connection.transaction() as conn:
            cursor = await conn.execute('''
                SELECT value FROM cache 
                WHERE key = ? AND expires_at > datetime(?)
            ''', (key, datetime.now().timestamp()))
            
            result = await cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None

    async def cleanup_expired_cache(self):
        """Remove expired cache entries."""
        async with self._connection.transaction() as conn:
            await conn.execute('''
                DELETE FROM cache 
                WHERE expires_at <= datetime(?)
            ''', (datetime.now().timestamp(),))
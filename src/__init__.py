# src/__init__.py
"""
VRP Optimizer package.
"""
from .core import *
from .database import Database
from .services import *

__version__ = "1.0.0"

# src/database/__init__.py
from .database import Database

__all__ = ['Database']

# src/database/database.py
from typing import Optional
import aiosqlite
from core.config import settings

class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """Initialize database connection."""
        self.db = await aiosqlite.connect(
            self.settings.database_path
        )
        await self._create_tables()
    
    async def _create_tables(self):
        """Create necessary tables."""
        if self.db:
            await self.db.execute('''
                CREATE TABLE IF NOT EXISTS geocoding_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location_key TEXT UNIQUE,
                    latitude REAL,
                    longitude REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await self.db.commit()
    
    async def close(self):
        """Close database connection."""
        if self.db:
            await self.db.close()

# src/services/base_service.py
from core.config import Settings
from database import Database
import logging
from typing import Optional

class BaseService:
    """Base class for all services."""
    
    def __init__(self, settings: Settings, database: Optional[Database] = None):
        self.settings = settings
        self.database = database
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def cleanup(self):
        """Cleanup service resources."""
        pass

# Update all service imports to use relative imports:

# src/services/geocoding_service.py
from database import Database
from src.services.base_service import BaseService

# src/services/data_service.py
from database import Database
from src.services.base_service import BaseService

# src/services/optimization_service.py
from database import Database
from src.services.base_service import BaseService

# src/services/visualization_service.py
from src.services.base_service import BaseService

# ui/streamlit_app.py
from src.database import Database
from src.services import (
    DataService,
    OptimizationService,
    VisualizationService
)
from src.core.config import Settings

# Create settings first
settings = Settings()

# Initialize database
database = Database(settings)

# Initialize services
data_service = DataService(settings, database)
optimization_service = OptimizationService(settings, database)
visualization_service = VisualizationService(settings)
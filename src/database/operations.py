# src/database/migrations.py

import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from src.core.models import Base
from src.core.settings import Settings


async def init_db(settings: Settings):
    """Initialize database with all tables."""
    # Create data directory if it doesn't exist
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)

    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    return engine

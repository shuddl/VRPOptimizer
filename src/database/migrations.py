import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
from src.core.settings import Settings

Base = declarative_base()


async def init_db(settings: Settings):
    """Initialize database with all tables."""
    # Create data directory if it doesn't exist
    data_dir = Path("./data")
    if not data_dir.exists():
        print(f"Creating data directory at: {data_dir.resolve()}")
        data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to database at: {settings.DATABASE_URL}")

    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize database: {str(e)}")
        raise

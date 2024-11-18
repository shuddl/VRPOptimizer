import asyncio
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base

# Load environment variables from .env file
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.settings import Settings
from src.database.database import (
    Base,
)  # Ensure Base is imported from the correct module

print(f"Environment DATABASE_URL: {os.environ.get('DATABASE_URL')}")


async def main():
    """Initialize the database."""
    try:
        # Print loaded settings for debugging
        settings = Settings()
        print(f"Current settings: {settings.model_dump()}")
        print(f"DATABASE_URL from settings: {settings.DATABASE_URL}")

        print("Initializing database...")

        engine = create_async_engine(settings.DATABASE_URL, echo=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

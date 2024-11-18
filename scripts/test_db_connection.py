# test_db_connection.py

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def main():
    engine = create_async_engine(
        "sqlite+aiosqlite:////Users/spencerpro/Desktop/projects/vrp_optimizer/data/vrp_optimizer.db",
        echo=True,
    )
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print(result.scalar())


if __name__ == "__main__":
    asyncio.run(main())

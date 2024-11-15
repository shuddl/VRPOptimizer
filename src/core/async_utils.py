# src/core/async_utils.py

import asyncio
import nest_asyncio

# Allow nested event loops
nest_asyncio.apply()


class AsyncLoopManager:
    """Singleton manager for async operations."""

    _instance = None
    _loop = asyncio.get_event_loop()

    @classmethod
    def get_loop(cls):
        return cls._loop

    @classmethod
    def run_async(cls, coro):
        """Run an async coroutine in the managed event loop."""
        if coro is None:
            raise ValueError("Expected a coroutine object, got None")
        loop = cls.get_loop()
        return asyncio.run_coroutine_threadsafe(coro, loop).result()

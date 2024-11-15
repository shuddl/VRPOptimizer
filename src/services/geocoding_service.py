import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
import asyncio
import aiohttp
from redis import asyncio as aioredis
from ratelimit import limits, sleep_and_retry
from googlemaps import Client
from src.core.models import CacheEntry, Location
from src.core.settings import Settings
from src.database.database import DatabaseConnection
from src.services.base_service import BaseService


class GeocodingService(BaseService):
    """Production-ready geocoding service with failover and caching."""

    def __init__(self, settings: Settings, database: DatabaseConnection):
        super().__init__(settings, database)
        self.session = None
        self.cache_timeout = timedelta(days=30)
        self.gmaps = Client(key=settings.GEOCODING_API_KEY)
        self.redis = None
        self.redis_settings = settings.redis_settings

    async def ensure_initialized(self):
        await super().ensure_initialized()
        await self._initialize_session()
        if self.redis is None:
            try:
                self.redis = await aioredis.from_url(
                    self.redis_settings["url"],
                    password=self.redis_settings["password"],
                    ssl=self.redis_settings["ssl"],
                    socket_timeout=self.redis_settings["timeout"],
                    retry_on_timeout=True,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                self.logger.error(f"Failed to initialize Redis connection: {str(e)}")
                # Optionally, you might want to continue without Redis
                self.redis = None

    async def _initialize_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def cleanup(self):
        """Cleanup resources before exit."""
        if self.session:
            await self.session.close()
        if self.redis:
            await self.redis.close()
        await super().cleanup()

    @limits(calls=1, period=1)  # 1 call per second
    async def geocode_location(
        self, location: Location
    ) -> Optional[Tuple[float, float]]:
        """Geocode a location with caching and failover."""
        await self.ensure_initialized()
        try:
            # Check cache first
            cache_key = f"{location.city.lower()},{location.state.lower()}"
            cached = await self._get_from_cache(cache_key)
            if cached:
                return cached

            # Geocode with Google Maps
            address = f"{location.city}, {location.state}, USA"
            result = self.gmaps.geocode(address)

            if result and len(result) > 0:
                location = result[0]["geometry"]["location"]
                lat, lng = location["lat"], location["lng"]

                # Cache the result
                await self._save_to_cache(cache_key, (lat, lng))

                return lat, lng

            self.logger.warning(
                f"Geocoding failed for {location.city}, {location.state}"
            )
            return None

        except Exception as e:
            self.logger.error(f"Geocoding error: {str(e)}")
            raise

    async def geocode_locations(
        self, locations: List[Location]
    ) -> Dict[str, Tuple[float, float]]:
        """Batch geocode multiple locations with caching and failover."""
        await self.ensure_initialized()
        results = {}
        try:
            # Check cache first
            cache_keys = [
                f"{loc.city.lower()},{loc.state.lower()}" for loc in locations
            ]
            cached_results = await self._get_batch_from_cache(cache_keys)
            results.update(cached_results)

            # Geocode remaining locations
            remaining_locations = [
                loc
                for loc in locations
                if f"{loc.city.lower()},{loc.state.lower()}" not in results
            ]
            if remaining_locations:
                addresses = [
                    f"{loc.city}, {loc.state}, USA" for loc in remaining_locations
                ]
                geocode_results = self.gmaps.geocode(addresses)

                for loc, result in zip(remaining_locations, geocode_results):
                    if result and len(result) > 0:
                        location = result[0]["geometry"]["location"]
                        lat, lng = location["lat"], location["lng"]
                        cache_key = f"{loc.city.lower()},{loc.state.lower()}"
                        results[cache_key] = (lat, lng)
                        await self._save_to_cache(cache_key, (lat, lng))
                    else:
                        self.logger.warning(
                            f"Geocoding failed for {loc.city}, {loc.state}"
                        )

            return results

        except Exception as e:
            self.logger.error(f"Batch geocoding error: {str(e)}")
            raise

    async def _get_from_cache(self, cache_key: str) -> Optional[Tuple[float, float]]:
        """Get coordinates from cache with fallback to database."""
        try:
            if self.redis:
                cached = await self.redis.get(cache_key)
                if cached:
                    lat, lng = map(float, cached.split(","))
                    return lat, lng
            
            # Fallback to database cache
            return await self.database.get_cached_coordinates(cache_key)
        except Exception as e:
            self.logger.error(f"Cache retrieval error: {str(e)}")
            return None

    async def _get_batch_from_cache(
        self, cache_keys: List[str]
    ) -> Dict[str, Tuple[float, float]]:
        """Get multiple coordinates from cache."""
        await self.ensure_initialized()
        results = {}
        try:
            cached_values = await self.redis.mget(*cache_keys)
            for key, value in zip(cache_keys, cached_values):
                if value:
                    lat, lng = map(float, value.decode().split(","))
                    results[key] = (lat, lng)
            return results

        except Exception as e:
            self.logger.error(f"Batch cache retrieval error: {str(e)}")
            return results

    async def _save_to_cache(self, cache_key: str, coords: Tuple[float, float]):
        """Save coordinates to cache."""
        await self.ensure_initialized()
        try:
            await self.redis.setex(
                cache_key,
                int(self.cache_timeout.total_seconds()),
                f"{coords[0]},{coords[1]}",
            )

        except Exception as e:
            self.logger.error(f"Cache save error: {str(e)}")

    async def fetch_coordinates(self, address: str) -> Optional[Dict[str, float]]:
        await self.ensure_initialized()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.example.com/geocode?address={address}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"latitude": data["lat"], "longitude": data["lon"]}
                return None

    async def some_async_method(self):
        await self.ensure_initialized()
        # ... other initialization

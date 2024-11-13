import aiohttp
import asyncio
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta
from src.database import Database
from src.core.models import Location
import logging
from ratelimit import limits, sleep_and_retry

class GeocodingService:
    """Production-ready geocoding service with failover and caching."""
    
    def __init__(self, database: Database, settings: Settings):
        self.db = database
        self.settings = settings
        self.session = None
        self.logger = logging.getLogger(__name__)
        self.cache_timeout = timedelta(days=30)
        self._initialize_session()

    async def _initialize_session(self):
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)

    @sleep_and_retry
    @limits(calls=1, period=1)  # 1 call per second
    async def geocode_location(self, location: Location) -> Optional[Tuple[float, float]]:
        """Geocode a location with caching and failover."""
        try:
            # Check cache first
            cache_key = f"{location.city.lower()},{location.state.lower()}"
            cached = await self._get_from_cache(cache_key)
            if cached:
                return cached

            # Try primary service (OpenStreetMap)
            coords = await self._geocode_openstreetmap(location)
            if coords:
                await self._save_to_cache(cache_key, coords)
                return coords

            # Failover to backup service
            coords = await self._geocode_backup(location)
            if coords:
                await self._save_to_cache(cache_key, coords)
                return coords

            self.logger.warning(f"Geocoding failed for {location.city}, {location.state}")
            return None

        except Exception as e:
            self.logger.error(f"Geocoding error: {str(e)}")
            raise

    async def _get_from_cache(self, cache_key: str) -> Optional[Tuple[float, float]]:
        """Get coordinates from cache."""
        try:
            async with self.db.session_scope() as session:
                entry = await session.query(CacheEntry).filter(
                    CacheEntry.location_key == cache_key,
                    CacheEntry.updated_at >= datetime.now() - self.cache_timeout
                ).first()
                
                if entry:
                    return (entry.latitude, entry.longitude)
                return None
                
        except Exception as e:
            self.logger.error(f"Cache retrieval error: {str(e)}")
            return None

    async def _save_to_cache(self, cache_key: str, coords: Tuple[float, float]):
        """Save coordinates to cache."""
        try:
            async with self.db.session_scope() as session:
                entry = await session.query(CacheEntry).filter(
                    CacheEntry.location_key == cache_key
                ).first()
                
                if entry:
                    entry.latitude = coords[0]
                    entry.longitude = coords[1]
                    entry.updated_at = datetime.now()
                else:
                    entry = CacheEntry(
                        location_key=cache_key,
                        latitude=coords[0],
                        longitude=coords[1],
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    session.add(entry)
                    
        except Exception as e:
            self.logger.error(f"Cache save error: {str(e)}")

    async def _geocode_openstreetmap(self, location: Location) -> Optional[Tuple[float, float]]:
        """Geocode using OpenStreetMap with retries."""
        for attempt in range(self.settings.MAX_RETRIES):
            try:
                async with self.session.get(
                    'https://nominatim.openstreetmap.org/search',
                    params={
                        'city': location.city,
                        'state': location.state,
                        'country': 'USA',
                        'format': 'json',
                        'limit': 1
                    },
                    headers={'User-Agent': 'VRPOptimizer/1.0'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            return (float(data[0]['lat']), float(data[0]['lon']))
                    elif response.status == 429:  # Rate limited
                        await asyncio.sleep(2 ** attempt)
                        continue
                        
            except Exception as e:
                self.logger.error(f"OpenStreetMap geocoding error: {str(e)}")
                if attempt < self.settings.MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                break
                
        return None

    async def _geocode_backup(self, location: Location) -> Optional[Tuple[float, float]]:
        """Backup geocoding service implementation."""
        # Implement backup service here
        return None
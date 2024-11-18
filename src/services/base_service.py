# src/services/base_service.py
import logging
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime
import structlog
from pathlib import Path
from src.core.settings import Settings
from src.core.exceptions import VRPOptimizerError
from src.database.database import DatabaseConnection
from src.monitoring.monitoring import MonitoringSystem
from src.core.settings import Settings
import logging
from typing import Optional


class ServiceError(VRPOptimizerError):
    """Base exception for service-level errors."""

    pass


class BaseService:
    """Base class for all services."""

    def __init__(self, settings: Settings, database: DatabaseConnection):
        self.settings = settings
        self.database = database
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False  # Initialize the _initialized attribute

    async def ensure_initialized(self):
        """Ensure service is properly initialized."""
        if not self._initialized:
            await self._initialize()
            self._initialized = True

    async def _initialize(self) -> None:
        """Initialize service resources."""
        try:
            # Ensure database connection if needed
            if self.database and not self.database.is_connected:
                await self.database.initialize()

            # Initialize monitoring if available
            if hasattr(self, "monitoring") and self.monitoring:
                await self.monitoring.register_service(self.__class__.__name__)

            self.logger.info("Service initialized successfully")

        except Exception as e:
            self.logger.error(f"Service initialization failed: {str(e)}")
            raise ServiceError(
                f"Failed to initialize {self.__class__.__name__}: {str(e)}"
            )

    async def cleanup(self) -> None:
        """Cleanup service resources."""
        try:
            # Implement cleanup logic in derived classes
            pass
        except Exception as e:
            self.logger.error("Service cleanup failed", error=str(e))

    async def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        async with self._lock:
            return {
                "service_name": self.__class__.__name__,
                "operations_total": self.metrics["operations_total"],
                "errors_total": self.metrics["errors_total"],
                "avg_operation_duration": self._calculate_avg_duration(),
                "last_error": self.metrics["last_error"],
                "last_operation": self.metrics["last_operation"],
            }

    def _calculate_avg_duration(self) -> float:
        """Calculate average operation duration."""
        durations = self.metrics["operation_duration"]
        if not durations:
            return 0.0
        return sum(durations) / len(durations)

    async def _record_operation(
        self,
        operation_name: str,
        duration: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record operation metrics."""
        async with self._lock:
            self.metrics["operations_total"] += 1
            self.metrics["operation_duration"].append(duration)
            self.metrics["last_operation"] = {
                "name": operation_name,
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "success": success,
            }

            if not success:
                self.metrics["errors_total"] += 1
                self.metrics["last_error"] = {
                    "operation": operation_name,
                    "timestamp": datetime.now().isoformat(),
                    "error": error,
                }

            # Keep only last 1000 duration measurements
            if len(self.metrics["operation_duration"]) > 1000:
                self.metrics["operation_duration"] = self.metrics["operation_duration"][
                    -1000:
                ]

    async def _execute_operation(
        self, operation_name: str, operation, *args, **kwargs
    ) -> Any:
        """
        Execute an operation with metrics and error handling.

        Args:
            operation_name: Name of the operation
            operation: Async function to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Operation result

        Raises:
            ServiceError: If operation fails
        """
        start_time = datetime.now()
        try:
            result = await operation(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()

            await self._record_operation(operation_name, duration, success=True)

            # Log to monitoring if available
            if self.monitoring:
                await self.monitoring.log_operation(
                    self.__class__.__name__, operation_name, duration, success=True
                )

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)

            await self._record_operation(
                operation_name, duration, success=False, error=error_msg
            )

            # Log to monitoring if available
            if self.monitoring:
                await self.monitoring.log_operation(
                    self.__class__.__name__,
                    operation_name,
                    duration,
                    success=False,
                    error=error_msg,
                )

            self.logger.error(
                "Operation failed",
                operation=operation_name,
                error=error_msg,
                duration=duration,
            )

            raise ServiceError(f"{operation_name} failed: {error_msg}")

    async def _cache_result(self, key: str, value: Any, expires_in: int = 3600) -> None:
        """
        Cache operation result.

        Args:
            key: Cache key
            value: Value to cache
            expires_in: Cache duration in seconds (default: 1 hour)
        """
        if self.database:
            await self.database.set_cache(key, value, expires_in)

    async def _get_cached_result(self, key: str) -> Optional[Any]:
        """
        Get cached result.

        Args:
            key: Cache key

        Returns:
            Cached value if available
        """
        if self.database:
            return await self.database.get_cache(key)
        return None

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate cache key from arguments.

        Args:
            prefix: Key prefix
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(key_parts)

    @staticmethod
    def is_valid_operation(operation_name: str) -> bool:
        """
        Validate operation name.

        Args:
            operation_name: Name to validate

        Returns:
            bool: True if valid
        """
        return bool(operation_name and isinstance(operation_name, str))

    async def ensure_services(self):
        """Ensure all required services are running."""
        if self.database and not await self.database.check_connection():
            self.logger.warning("Database connection lost, attempting to reconnect...")
            await self.database.initialize()

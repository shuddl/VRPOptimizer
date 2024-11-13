# src/services/base_service.py

import logging
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime
import structlog
from pathlib import Path

from ..core.config import Settings
from ..core.exceptions import VRPOptimizerError
from ..database import Database
from ..monitoring import MonitoringSystem

class ServiceError(VRPOptimizerError):
    """Base exception for service-level errors."""
    pass

class BaseService:
    """Base class for all services in the VRP Optimizer."""

    def __init__(
        self,
        settings: Settings,
        database: Optional[Database] = None,
        monitoring: Optional[MonitoringSystem] = None
    ):
        """
        Initialize base service.

        Args:
            settings: Application settings
            database: Optional database connection
            monitoring: Optional monitoring system
        """
        self.settings = settings
        self.database = database
        self.monitoring = monitoring
        self._setup_logging()
        self._initialize_metrics()
        self._lock = asyncio.Lock()

    def _setup_logging(self) -> None:
        """Setup structured logging for the service."""
        self.logger = structlog.get_logger(self.__class__.__name__)
        self.logger = self.logger.bind(
            service=self.__class__.__name__,
            environment=self.settings.environment
        )

    def _initialize_metrics(self) -> None:
        """Initialize service-specific metrics."""
        self.metrics = {
            'operations_total': 0,
            'errors_total': 0,
            'operation_duration': [],
            'last_error': None,
            'last_operation': None
        }

    async def initialize(self) -> None:
        """Initialize service resources."""
        try:
            # Ensure database connection if needed
            if self.database and not self.database.is_connected:
                await self.database.initialize()

            # Initialize monitoring if available
            if self.monitoring:
                await self.monitoring.register_service(self.__class__.__name__)

            self.logger.info("Service initialized successfully")

        except Exception as e:
            self.logger.error("Service initialization failed", error=str(e))
            raise ServiceError(f"Failed to initialize {self.__class__.__name__}: {str(e)}")

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
                'service_name': self.__class__.__name__,
                'operations_total': self.metrics['operations_total'],
                'errors_total': self.metrics['errors_total'],
                'avg_operation_duration': self._calculate_avg_duration(),
                'last_error': self.metrics['last_error'],
                'last_operation': self.metrics['last_operation']
            }

    def _calculate_avg_duration(self) -> float:
        """Calculate average operation duration."""
        durations = self.metrics['operation_duration']
        if not durations:
            return 0.0
        return sum(durations) / len(durations)

    async def _record_operation(
        self,
        operation_name: str,
        duration: float,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Record operation metrics."""
        async with self._lock:
            self.metrics['operations_total'] += 1
            self.metrics['operation_duration'].append(duration)
            self.metrics['last_operation'] = {
                'name': operation_name,
                'timestamp': datetime.now().isoformat(),
                'duration': duration,
                'success': success
            }

            if not success:
                self.metrics['errors_total'] += 1
                self.metrics['last_error'] = {
                    'operation': operation_name,
                    'timestamp': datetime.now().isoformat(),
                    'error': error
                }

            # Keep only last 1000 duration measurements
            if len(self.metrics['operation_duration']) > 1000:
                self.metrics['operation_duration'] = self.metrics['operation_duration'][-1000:]

    async def _execute_operation(
        self,
        operation_name: str,
        operation,
        *args,
        **kwargs
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
            
            await self._record_operation(
                operation_name,
                duration,
                success=True
            )

            # Log to monitoring if available
            if self.monitoring:
                await self.monitoring.log_operation(
                    self.__class__.__name__,
                    operation_name,
                    duration,
                    success=True
                )

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)

            await self._record_operation(
                operation_name,
                duration,
                success=False,
                error=error_msg
            )

            # Log to monitoring if available
            if self.monitoring:
                await self.monitoring.log_operation(
                    self.__class__.__name__,
                    operation_name,
                    duration,
                    success=False,
                    error=error_msg
                )

            self.logger.error(
                "Operation failed",
                operation=operation_name,
                error=error_msg,
                duration=duration
            )

            raise ServiceError(f"{operation_name} failed: {error_msg}")

    async def _cache_result(
        self,
        key: str,
        value: Any,
        expires_in: int = 3600
    ) -> None:
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
# src/monitoring/monitoring.py

import logging
import psutil
import threading
from datetime import datetime
from typing import Dict, List, Optional
from prometheus_client import Counter, Gauge, Histogram
import structlog
from ..core.exceptions import ResourceExhaustedError

class MonitoringSystem:
    """System monitoring and metrics collection."""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = structlog.get_logger(__name__)
        self.is_monitoring = False
        self._setup_metrics()
        self.monitoring_thread = None

    def _setup_metrics(self):
        """Initialize Prometheus metrics."""
        self.metrics = {
            'optimization_count': Counter(
                'vrp_optimizations_total',
                'Total number of optimization runs'
            ),
            'optimization_duration': Histogram(
                'vrp_optimization_duration_seconds',
                'Time spent on optimization',
                buckets=[10, 30, 60, 120, 300]
            ),
            'active_optimizations': Gauge(
                'vrp_active_optimizations',
                'Currently running optimizations'
            ),
            'memory_usage': Gauge(
                'vrp_memory_usage_bytes',
                'Current memory usage'
            ),
            'cpu_usage': Gauge(
                'vrp_cpu_usage_percent',
                'Current CPU usage percentage'
            ),
            'error_count': Counter(
                'vrp_errors_total',
                'Total number of errors',
                ['type']
            )
        }

    def start_monitoring(self):
        """Start system monitoring."""
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitor_system)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        self.logger.info("System monitoring started")

    def stop_monitoring(self):
        """Stop system monitoring."""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        self.logger.info("System monitoring stopped")

    def _monitor_system(self):
        """Monitor system metrics periodically."""
        while self.is_monitoring:
            try:
                # Update system metrics
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)
                
                self.metrics['memory_usage'].set(memory.used)
                self.metrics['cpu_usage'].set(cpu)

                # Check thresholds
                if memory.percent > 90:
                    self.logger.warning("High memory usage", memory_percent=memory.percent)
                if cpu > 80:
                    self.logger.warning("High CPU usage", cpu_percent=cpu)

                # Update disk metrics if needed
                disk = psutil.disk_usage('/')
                if disk.percent > 90:
                    self.logger.warning("Low disk space", disk_percent=disk.percent)

            except Exception as e:
                self.logger.error("Monitoring error", error=str(e))

            threading.Event().wait(5)  # Wait 5 seconds between updates

    async def log_optimization_start(self, num_shipments: int):
        """Log the start of an optimization run."""
        self.metrics['optimization_count'].inc()
        self.metrics['active_optimizations'].inc()
        
        self.logger.info(
            "Optimization started",
            num_shipments=num_shipments,
            timestamp=datetime.now().isoformat()
        )

    async def log_optimization_end(self, duration: float, success: bool, error: Optional[str] = None):
        """Log the completion of an optimization run."""
        self.metrics['active_optimizations'].dec()
        self.metrics['optimization_duration'].observe(duration)

        if not success:
            self.metrics['error_count'].labels(type='optimization').inc()
            self.logger.error(
                "Optimization failed",
                duration=duration,
                error=error
            )
        else:
            self.logger.info(
                "Optimization completed",
                duration=duration
            )

    async def get_system_health(self) -> Dict:
        """Get current system health metrics."""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        disk = psutil.disk_usage('/')

        return {
            'memory_used_percent': memory.percent,
            'cpu_percent': cpu,
            'disk_used_percent': disk.percent,
            'active_optimizations': self.metrics['active_optimizations']._value.get(),
            'total_optimizations': self.metrics['optimization_count']._value.get(),
            'timestamp': datetime.now().isoformat()
        }

    def log_error(self, error: Exception, context: Dict = None):
        """Log an error with context."""
        self.metrics['error_count'].labels(type=type(error).__name__).inc()
        
        self.logger.error(
            "Error occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {}
        )

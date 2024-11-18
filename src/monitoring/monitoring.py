# src/monitoring/monitoring.py

import base64
import logging
import psutil
import threading
import time
from datetime import datetime
from typing import Optional, Dict
from prometheus_client import Counter, Gauge, Histogram, REGISTRY
import structlog
from src.core.settings import Settings
import asyncio
import streamlit as st


class MonitoringSystem:
    """System monitoring and metrics collection."""

    _instance = None
    _initialized = False

    def __new__(cls, settings: Settings = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings: Settings = None):
        if not self._initialized and settings is not None:
            self.settings = settings
            self.logger = structlog.get_logger(__name__)
            self.metrics = {}
            self._setup_metrics()

            # Validate resource limits for VisualizationService
            self._validate_resource_limits()

            # Create an event loop for the monitoring task
            self.loop = asyncio.new_event_loop()
            self.monitoring_task = self.loop.create_task(self.monitor_system())
            self.__class__._initialized = True

    def _setup_metrics(self):
        """Initialize Prometheus metrics."""
        # Clear any existing metrics with same names
        for metric in list(REGISTRY._names_to_collectors.keys()):
            if metric.startswith("vrp_"):
                try:
                    REGISTRY.unregister(REGISTRY._names_to_collectors[metric])
                except KeyError:
                    pass  # Metric not registered; ignore

        # Initialize new metrics
        self.metrics = {
            "optimization_count": Counter(
                "vrp_optimizations_total", "Total number of optimization runs"
            ),
            "optimization_duration": Histogram(
                "vrp_optimization_duration_seconds",
                "Time spent on optimization",
                buckets=[10, 30, 60, 120, 300],
            ),
            "active_optimizations": Gauge(
                "vrp_active_optimizations", "Currently running optimizations"
            ),
            "memory_usage": Gauge(
                "vrp_memory_usage_bytes", "Current memory usage in bytes"
            ),
            "cpu_usage": Gauge("vrp_cpu_usage_percent", "Current CPU usage percentage"),
        }

    def _validate_resource_limits(self):
        """Validate and adjust resource limits for VisualizationService."""
        # Example resource limits (replace with actual settings)
        max_cpu_limit = 100  # Example maximum CPU limit
        max_memory_limit = 32768  # Example maximum memory limit in MB

        cpu_limit = getattr(self.settings, "VISUALIZATION_CPU_LIMIT", max_cpu_limit)
        memory_limit = getattr(
            self.settings, "VISUALIZATION_MEMORY_LIMIT", max_memory_limit
        )

        if cpu_limit > max_cpu_limit:
            self.logger.warning(
                f"Invalid CPU limit value: {cpu_limit}. Using system default {max_cpu_limit}."
            )
            self.settings.VISUALIZATION_CPU_LIMIT = max_cpu_limit

        if memory_limit > max_memory_limit:
            self.logger.warning(
                f"Invalid memory limit value: {memory_limit}. Using system default {max_memory_limit}."
            )
            self.settings.VISUALIZATION_MEMORY_LIMIT = max_memory_limit

    async def monitor_system(self):
        """Background task to monitor system resources."""
        while True:
            try:
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)

                self.metrics["memory_usage"].set(memory.used)
                self.metrics["cpu_usage"].set(cpu)

                # Check thresholds
                if memory.percent > 90:
                    self.logger.warning(
                        "High memory usage", memory_percent=memory.percent
                    )
                if cpu > 80:
                    self.logger.warning("High CPU usage", cpu_percent=cpu)

                # Update disk metrics if needed
                disk = psutil.disk_usage("/")
                if disk.percent > 90:
                    self.logger.warning("Low disk space", disk_percent=disk.percent)
            except Exception as e:
                self.logger.error("Monitoring error", error=str(e))

            await asyncio.sleep(5)  # Wait 5 seconds between updates

    def log_error(self, error: Exception):
        """Log an error within the monitoring system."""
        self.logger.error("An error occurred", error=str(error))
        # Increment an error counter if desired

    async def get_system_health(self) -> Dict:
        """Get current system health metrics."""
        try:
            memory = psutil.virtual_memory()
            metrics = {
                "memory_percent": memory.percent,
                "cpu_percent": psutil.cpu_percent(interval=1),
                "active_optimizations": self.metrics[
                    "active_optimizations"
                ]._value.get(),
                "total_optimizations": self.metrics["optimization_count"]._value.get(),
            }
            return metrics
        except Exception as e:
            self.logger.error("Error getting system health", error=str(e))
            return {
                "memory_percent": 0,
                "cpu_percent": 0,
                "active_optimizations": 0,
                "total_optimizations": 0,
            }

    async def log_optimization_start(self, num_shipments: int):
        """Log the start of an optimization run."""
        self.metrics["active_optimizations"].inc()
        self.metrics["optimization_count"].inc()
        self.logger.info("Starting optimization", num_shipments=num_shipments)

    async def log_optimization_end(
        self, duration: float, success: bool, error: str = None
    ):
        """Log the end of an optimization run."""
        self.metrics["active_optimizations"].dec()
        self.metrics["optimization_duration"].observe(duration)
        if success:
            self.logger.info("Optimization completed", duration=duration)
        else:
            self.logger.error("Optimization failed", duration=duration, error=error)

    def clear_cache(self):
        """Clear the monitoring system's cache."""
        self.cache = {}
        self.logger.info("Monitoring cache cleared successfully")


# streamlit_app.py


def _export_solution(services, solution):
    """Export the solution to Excel with error handling."""
    try:
        excel_data = services.data_service.export_solution(solution, "excel")

        if excel_data:
            b64 = base64.b64encode(excel_data).decode()
            href = f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}"
            st.markdown(
                f'<a href="{href}" download="route_solution.xlsx">Download Solution (Excel)</a>',
                unsafe_allow_html=True,
            )
        else:
            st.error("Failed to export solution")

    except Exception as e:
        st.error(f"Error exporting solution: {str(e)}")
        services.monitoring.log_error(e)


def _display_solution_summary(services, solution):
    """Display a summary of the optimization solution."""
    services.metrics_panel.render(solution)
    services.shipment_table.render(solution)

    # [Rest of the code remains unchanged...]

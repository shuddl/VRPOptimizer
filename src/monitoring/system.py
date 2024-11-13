# monitoring/system.py
import logging
import logging.handlers
from typing import Dict, Any, Optional
import time
import psutil
import threading
from datetime import datetime
import json
from pathlib import Path
import structlog
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import traceback
from dataclasses import dataclass
import asyncio
import aiofiles
import aiohttp

@dataclass
class SystemMetrics:
    """System metrics data structure."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_threads: int
    timestamp: datetime

class MonitoringSystem:
    """Production-ready monitoring system with metrics collection."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = self._setup_logging()
        self._setup_metrics()
        self.monitoring_thread = None
        self.is_monitoring = False
        self.metrics_history: List[SystemMetrics] = []
        
        # Create monitoring directories
        self.settings.LOG_DIR.mkdir(exist_ok=True)
        
        # Start Prometheus metrics server
        start_http_server(8000)

    def _setup_logging(self) -> structlog.BoundLogger:
        """Configure structured logging."""
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Set up file handler with rotation
        log_file = self.settings.LOG_DIR / "vrp_optimizer.log"
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        
        # Set up console handler
        console_handler = logging.StreamHandler()
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            handlers=[handler, console_handler],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        return structlog.get_logger()

    def _setup_metrics(self):
        """Initialize Prometheus metrics."""
        self.metrics = {
            'optimization_duration': Histogram(
                'optimization_duration_seconds',
                'Time spent on optimization',
                buckets=[10, 30, 60, 120, 300, 600]
            ),
            'optimization_count': Counter(
                'optimization_total',
                'Total number of optimizations'
            ),
            'optimization_errors': Counter(
                'optimization_errors_total',
                'Total number of optimization errors'
            ),
            'active_optimizations': Gauge(
                'active_optimizations',
                'Number of currently running optimizations'
            ),
            'memory_usage': Gauge(
                'memory_usage_percent',
                'System memory usage percentage'
            ),
            'cpu_usage': Gauge(
                'cpu_usage_percent',
                'System CPU usage percentage'
            ),
            'shipments_processed': Counter(
                'shipments_processed_total',
                'Total number of shipments processed'
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
                metrics = SystemMetrics(
                    cpu_percent=psutil.cpu_percent(interval=1),
                    memory_percent=psutil.virtual_memory().percent,
                    disk_usage_percent=psutil.disk_usage('/').percent,
                    active_threads=threading.active_count(),
                    timestamp=datetime.now()
                )
                
                self.metrics_history.append(metrics)
                
                # Update Prometheus metrics
                self.metrics['memory_usage'].set(metrics.memory_percent)
                self.metrics['cpu_usage'].set(metrics.cpu_percent)
                
                # Check thresholds
                self._check_thresholds(metrics)
                
                # Trim history if too long
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-1000:]
                
                time.sleep(5)  # Monitor every 5 seconds
                
            except Exception as e:
                self.logger.error("Monitoring error", error=str(e))

    def _check_thresholds(self, metrics: SystemMetrics):
        """Check system metrics against thresholds."""
        if metrics.memory_percent > 90:
            self.logger.warning("High memory usage", memory_percent=metrics.memory_percent)
            
        if metrics.cpu_percent > 80:
            self.logger.warning("High CPU usage", cpu_percent=metrics.cpu_percent)
            
        if metrics.disk_usage_percent > 90:
            self.logger.warning("High disk usage", disk_percent=metrics.disk_usage_percent)

    async def log_optimization_start(self, num_shipments: int):
        """Log optimization job start."""
        self.metrics['optimization_count'].inc()
        self.metrics['active_optimizations'].inc()
        self.metrics['shipments_processed'].inc(num_shipments)
        
        self.logger.info(
            "Optimization started",
            num_shipments=num_shipments
        )

    async def log_optimization_end(self, duration: float, success: bool, error: Optional[str] = None):
        """Log optimization job completion."""
        self.metrics['active_optimizations'].dec()
        self.metrics['optimization_duration'].observe(duration)
        
        if not success:
            self.metrics['optimization_errors'].inc()
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

    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics."""
        if not self.metrics_history:
            return {}
            
        latest = self.metrics_history[-1]
        return {
            'cpu_percent': latest.cpu_percent,
            'memory_percent': latest.memory_percent,
            'disk_usage_percent': latest.disk_usage_percent,
            'active_threads': latest.active_threads,
            'active_optimizations': self.metrics['active_optimizations']._value.get(),
            'total_optimizations': self.metrics['optimization_count']._value.get(),
            'total_errors': self.metrics['optimization_errors']._value.get()
        }

    async def export_metrics(self, format: str = 'json') -> Optional[str]:
        """Export collected metrics."""
        try:
            metrics_data = {
                'system_metrics': [
                    {
                        'timestamp': m.timestamp.isoformat(),
                        'cpu_percent': m.cpu_percent,
                        'memory_percent': m.memory_percent,
                        'disk_usage_percent': m.disk_usage_percent,
                        'active_threads': m.active_threads
                    }
                    for m in self.metrics_history
                ],
                'optimization_metrics': {
                    'total_count': self.metrics['optimization_count']._value.get(),
                    'total_errors': self.metrics['optimization_errors']._value.get(),
                    'active_optimizations': self.metrics['active_optimizations']._value.get()
                }
            }

            if format == 'json':
                output_file = self.settings.LOG_DIR / f"metrics_{datetime.now():%Y%m%d_%H%M%S}.json"
                async with aiofiles.open(output_file, 'w') as f:
                    await f.write(json.dumps(metrics_data, indent=2))
                return str(output_file)
                
            else:
                self.logger.error("Unsupported export format", format=format)
                return None

        except Exception as e:
            self.logger.error("Metrics export failed", error=str(e))
            return None

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with context and stack trace."""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'stack_trace': traceback.format_exc(),
            'context': context or {}
        }
        
        self.logger.error("Error occurred", **error_data)


# monitoring/alerting.py
from enum import Enum
from typing import Optional, List
import smtplib
from email.mime.text import MIMEText
import requests

class AlertSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AlertingSystem:
    """Alerting system for critical events."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    async def send_alert(self, 
                        message: str,
                        severity: AlertSeverity,
                        context: Optional[Dict[str, Any]] = None):
        """Send alert through configured channels."""
        try:
            alert_data = {
                'timestamp': datetime.now().isoformat(),
                'severity': severity.value,
                'message': message,
                'context': context or {}
            }
            
            # Log alert
            self.logger.warning("Alert triggered", **alert_data)
            
            # Send through configured channels
            if severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
                await self._send_email_alert(alert_data)
                await self._send_slack_alert(alert_data)
                
        except Exception as e:
            self.logger.error("Alert sending failed", error=str(e))

    async def _send_email_alert(self, alert_data: Dict[str, Any]):
        """Send email alert."""
        if not self.settings.SMTP_SETTINGS:
            return
            
        try:
            msg = MIMEText(
                f"""
                Severity: {alert_data['severity']}
                Message: {alert_data['message']}
                Context: {json.dumps(alert_data['context'], indent=2)}
                Timestamp: {alert_data['timestamp']}
                """
            )
            
            msg['Subject'] = f"VRP Optimizer Alert: {alert_data['severity']}"
            msg['From'] = self.settings.SMTP_SETTINGS['from']
            msg['To'] = self.settings.SMTP_SETTINGS['to']
            
            with smtplib.SMTP(self.settings.SMTP_SETTINGS['host']) as server:
                server.send_message(msg)
                
        except Exception as e:
            self.logger.error("Email alert failed", error=str(e))

    async def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Send Slack alert."""
        if not self.settings.SLACK_WEBHOOK_URL:
            return
            
        try:
            payload = {
                'text': f"""
                *VRP Optimizer Alert*
                *Severity:* {alert_data['severity']}
                *Message:* {alert_data['message']}
                *Context:* ```{json.dumps(alert_data['context'], indent=2)}```
                *Timestamp:* {alert_data['timestamp']}
                """
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.settings.SLACK_WEBHOOK_URL,
                    json=payload
                ) as response:
                    if response.status != 200:
                        self.logger.error(
                            "Slack alert failed",
                            status=response.status,
                            response=await response.text()
                        )
                        
        except Exception as e:
            self.logger.error("Slack alert failed", error=str(e))
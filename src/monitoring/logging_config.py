# src/monitoring/logging_config.py

import logging
import logging.handlers
from pathlib import Path
import yaml
from typing import Optional
import structlog
from datetime import datetime

def setup_logging(config_path: Optional[Path] = None):
    """Configure logging with the specified configuration."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
            logging.config.dictConfig(config)
    else:
        _setup_default_logging()

def _setup_default_logging():
    """Set up default logging configuration."""
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

class LogManager:
    """Manage logging operations."""
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)
        
        # Set up handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up log handlers with rotation."""
        # Main log file
        main_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "vrp.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        main_handler.setFormatter(self._get_formatter())
        
        # Error log file
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "error.log",
            maxBytes=10*1024*1024,
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self._get_formatter())
        
        # Add handlers to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(main_handler)
        root_logger.addHandler(error_handler)

    def _get_formatter(self):
        """Create log formatter."""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def rotate_logs(self):
        """Force log rotation."""
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                handler.doRollover()

    def get_logs(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Retrieve logs within the specified time range."""
        logs = []
        log_file = self.log_dir / "vrp.log"
        
        if not log_file.exists():
            return logs

        with open(log_file) as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    log_time = datetime.fromisoformat(log_entry['timestamp'])
                    if start_time <= log_time <= end_time:
                        logs.append(log_entry)
                except:
                    continue

        return logs
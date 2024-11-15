import logging
import traceback
from typing import Dict, Any


class System:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
        }
        self.logger.error("Error occurred", **error_data)

        # Log stack trace separately to avoid memory-intensive operations
        self.logger.debug("Stack trace:", exc_info=True)

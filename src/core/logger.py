import json
import logging
import sys
from typing import Any, Dict
from src.core.config import settings

class StructuredFormatter(logging.Formatter):
    """Formats logs as JSON for integration with ELK, Datadog, or similar tools."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logger(name: str = "nlptosql") -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if setup_logger is called multiple times
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        
        handler = logging.StreamHandler(sys.stdout)
        
        if settings.DEBUG:
            # Human readable for local development
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        else:
            # JSON format for production
            formatter = StructuredFormatter()
            
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        logger.propagate = False
        
    return logger

logger = setup_logger()

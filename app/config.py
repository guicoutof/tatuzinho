"""
Configuration module for Tatuzinho application.

Loads environment variables and provides centralized configuration for:
- Database connections
- External API settings (SofaScore)
- Caching (Redis)
- Logging and debugging
"""

import os
import json
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tatuzinho_db")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# SofaScore API
SOFASCORE_API_BASE_URL = os.getenv("SOFASCORE_API_BASE_URL", "https://api.sofascore.com/api/v1")
SOFASCORE_RATE_LIMIT_DELAY = float(os.getenv("SOFASCORE_RATE_LIMIT_DELAY", "1.0"))
SOFASCORE_BATCH_SIZE = int(os.getenv("SOFASCORE_BATCH_SIZE", "50"))
SOFASCORE_MAX_RETRIES = int(os.getenv("SOFASCORE_MAX_RETRIES", "3"))
SOFASCORE_TIMEOUT = int(os.getenv("SOFASCORE_TIMEOUT", "30"))

# Redis / Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# App
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENV = os.getenv("ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Scraping
SCRAPER_ENABLED = os.getenv("SCRAPER_ENABLED", "True").lower() == "true"
BACKFILL_ENABLED = os.getenv("BACKFILL_ENABLED", "False").lower() == "true"
BACKFILL_YEARS = int(os.getenv("BACKFILL_YEARS", "2"))

# Predictions
PREDICTION_MODEL_PATH = os.getenv("PREDICTION_MODEL_PATH", "/tmp/prediction_model.pkl")
MIN_HISTORICAL_MATCHES = int(os.getenv("MIN_HISTORICAL_MATCHES", "5"))

# SofaScore Tournament IDs (hard-coded for performance)
# Copa do Mundo
WORLD_CUP_2026_ID = 17  # World Cup 2026
WORLD_CUP_2022_ID = 1   # World Cup 2022
# Eliminatórias 2026 (exemplos - buscar pelo endpoint)
QUALIFIERS_2026_IDS = []  # Preenchido dinamicamente


# ============ Logging Configuration ============

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging.
    
    Outputs log records as JSON objects with timestamp, level, logger name,
    message, module info, and optional exception details.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.
        
        Args:
            record: Log record to format.
        
        Returns:
            JSON-encoded log entry.
        """
        log_obj = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception details if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Merge extra context
        if hasattr(record, "extra_context"):
            log_obj.update(record.extra_context)
        
        return json.dumps(log_obj)


def setup_logging() -> logging.Logger:
    """Configure structured JSON logging with rotation.
    
    Sets up both console (development) and file (production) handlers with
    JSON formatting. Logs are rotated at 10MB with 5 backup files.
    
    Returns:
        Configured logger instance for the 'tatuzinho' application.
    
    Example:
        >>> logger = setup_logging()
        >>> logger.info("Application started", extra={"version": "1.0"})
    """
    logger = logging.getLogger("tatuzinho")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    # Remove any existing handlers
    logger.handlers.clear()
    
    # Console handler (development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # File handler with rotation (production)
    os.makedirs("logs", exist_ok=True)
    file_handler = RotatingFileHandler(
        "logs/tatuzinho.log",
        maxBytes=10_000_000,  # 10 MB
        backupCount=5,
    )
    file_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    return logger


# Initialize logger on module import
logger = setup_logging()

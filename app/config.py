import os
import json
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

env = os.environ.get("ENV", "development")
load_dotenv(f".env.{env}")
load_dotenv(".env", override=False)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tatuzinho_db")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENV = os.getenv("ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

SCRAPER_ENABLED = os.getenv("SCRAPER_ENABLED", "True").lower() == "true"
BACKFILL_ENABLED = os.getenv("BACKFILL_ENABLED", "False").lower() == "true"
BACKFILL_YEARS = int(os.getenv("BACKFILL_YEARS", "2"))

PREDICTION_MODEL_PATH = os.getenv("PREDICTION_MODEL_PATH", "/tmp/prediction_model.pkl")
MIN_HISTORICAL_MATCHES = int(os.getenv("MIN_HISTORICAL_MATCHES", "5"))


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_context"):
            log_obj.update(record.extra_context)
        return json.dumps(log_obj)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("tatuzinho")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    os.makedirs("logs", exist_ok=True)
    file_handler = RotatingFileHandler(
        "logs/tatuzinho.log",
        maxBytes=10_000_000,
        backupCount=5,
    )
    file_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()

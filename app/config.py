import os
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

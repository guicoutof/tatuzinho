from fastapi import FastAPI
import logging

from . import models, schemas
from .database import SessionLocal, engine
from .routers import tournaments, matches, teams, analytics


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
models.Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title="Tatuzinho - Football Analytics API",
    description="Análise de partidas de futebol com dados do SofaScore",
    version="1.0.0",
)

# Include routers
app.include_router(tournaments.router)
app.include_router(matches.router)
app.include_router(teams.router)
app.include_router(analytics.router)


# ============ Health Check ============
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# ============ Root endpoint ============
@app.get("/")
def root():
    """API root endpoint"""
    return {
        "name": "Tatuzinho - Football Analytics API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "tournaments": "/api/v1/tournaments",
            "matches": "/api/v1/matches",
            "teams": "/api/v1/teams",
            "analytics": "/api/v1/analytics",
        }
    }

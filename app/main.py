from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import models
from .database import SessionLocal, engine
from .config import logger
from .exceptions import TatuzinhoException
from .routers import tournaments, matches, teams, analytics, predictions


models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Tatuzinho - Football Analytics API",
    description="Análise de partidas de futebol com dados históricos",
    version="1.0.0",
)

app.include_router(tournaments.router)
app.include_router(matches.router)
app.include_router(teams.router)
app.include_router(analytics.router)
app.include_router(predictions.router)


@app.exception_handler(TatuzinhoException)
async def tatuzinho_exception_handler(
    request: Request,
    exc: TatuzinhoException,
) -> JSONResponse:
    status_code = 400

    exception_type = exc.__class__.__name__
    if "NotFound" in exception_type:
        status_code = 404
    elif "Duplicate" in exception_type:
        status_code = 409
    elif "Unauthorized" in exception_type or "Forbidden" in exception_type:
        status_code = 403

    logger.warning(
        f"Domain exception raised",
        extra={
            "exception_type": exception_type,
            "message": str(exc),
            "path": str(request.url.path),
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exception_type,
            "message": str(exc),
            "path": str(request.url.path),
            "status_code": status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        f"Unexpected exception",
        extra={
            "exception_type": exc.__class__.__name__,
            "message": str(exc),
            "path": str(request.url.path),
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "path": str(request.url.path),
            "status_code": 500,
        },
    )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> Dict[str, Any]:
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


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Application starting up")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Application shutting down")

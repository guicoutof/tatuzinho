"""
Main FastAPI application module.

Initializes the FastAPI app, sets up database, includes routers, and configures
exception handlers for consistent error handling across the application.
"""

from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import models
from .database import SessionLocal, engine
from .config import logger
from .exceptions import TatuzinhoException
from .routers import tournaments, matches, teams, analytics


# Create database tables
models.Base.metadata.create_all(bind=engine)

# FastAPI app initialization
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


# ============ Global Exception Handlers ============

@app.exception_handler(TatuzinhoException)
async def tatuzinho_exception_handler(
    request: Request,
    exc: TatuzinhoException,
) -> JSONResponse:
    """Handle all domain exceptions with consistent JSON response.
    
    Maps TatuzinhoException and its subclasses to appropriate HTTP status codes
    and returns structured error responses. All exceptions are logged with context.
    
    Args:
        request: FastAPI request object.
        exc: The exception that was raised.
    
    Returns:
        JSONResponse with error details and appropriate HTTP status code.
    """
    # Determine HTTP status code based on exception type
    status_code = 400  # Default for validation errors
    
    # Map specific exceptions to status codes
    exception_type = exc.__class__.__name__
    if "NotFound" in exception_type:
        status_code = 404
    elif "Duplicate" in exception_type:
        status_code = 409
    elif "Unauthorized" in exception_type or "Forbidden" in exception_type:
        status_code = 403
    
    # Log the error with context
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
    """Handle unexpected exceptions with generic error response.
    
    Logs all unexpected exceptions with full context for debugging.
    Returns a generic error message without exposing internal details.
    
    Args:
        request: FastAPI request object.
        exc: The exception that was raised.
    
    Returns:
        JSONResponse with generic error message.
    """
    # Log the full exception for debugging
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


# ============ Health Check ============

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring and load balancers.
    
    Returns:
        Dict with status 'ok' if application is running properly.
    """
    return {"status": "ok"}


# ============ Root Endpoint ============

@app.get("/")
async def root() -> Dict[str, Any]:
    """API root endpoint with service information.
    
    Returns:
        Dict containing service name, version, documentation URL, and available endpoints.
    """
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


# ============ Startup Events ============

@app.on_event("startup")
async def startup_event() -> None:
    """Run on application startup.
    
    Initializes resources like database connections, caches, and external clients.
    """
    logger.info("Application starting up")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Run on application shutdown.
    
    Cleans up resources like database connections and cache clients.
    """
    logger.info("Application shutting down")

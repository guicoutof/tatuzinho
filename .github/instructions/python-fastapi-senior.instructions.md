---
description: "Use when developing FastAPI backend code, implementing services/repositories, handling errors, caching, or working with SQLAlchemy. Covers senior-level Python/FastAPI architecture, type safety, error handling, and performance patterns for the Tatuzinho project."
applyTo: "**/*.py"
---

# Senior Python/FastAPI Development Guidelines - Tatuzinho

## 🏗️ Architecture Overview

Follow **strict layered architecture** with clear separation of concerns:

```
Routers (app/routers/*.py)
    ↓ (FastAPI endpoints, validation)
Services (app/services/*.py) ← Logic layer [NOT YET CREATED]
    ↓ (Business logic, orchestration, external APIs)
Repositories (app/repositories/*.py) ← Data access [NOT YET CREATED]
    ↓ (DB queries, abstraction, caching)
Models (app/models.py)
    ↓ (SQLAlchemy ORM, database schema)
Database (app/database.py)
```

### Layer Responsibilities

- **Routers**: Only request validation, response formatting, HTTP semantics
- **Services**: Business logic, data orchestration, external API calls
- **Repositories**: Database queries, caching strategies, data transformations
- **Models**: Pure ORM definitions, relationships, constraints

### ✅ DO
- Query database only in Repositories
- Call external APIs only in Services
- Use dependency injection with FastAPI `Depends()`
- Keep endpoints to 5-10 lines maximum

### ❌ DON'T
- Access `db.session` directly in routers
- Mix business logic with HTTP handling
- Use global variables for database connections
- Write queries inline in endpoints

---

## 🎯 Type Hints & Type Safety

**Enforce 100% type coverage** - every parameter and return type must be annotated.

### ✅ Correct

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from schemas import TournamentCreate, TournamentRead

def create_tournament(
    db: Session,
    tournament_in: TournamentCreate,
) -> TournamentRead:
    """Create a new tournament in the database.
    
    Args:
        db: Database session for persistence.
        tournament_in: Tournament creation schema with validation.
    
    Returns:
        TournamentRead: Newly created tournament with all fields.
    
    Raises:
        ValueError: If tournament name already exists.
    """
    existing = db.query(Tournament).filter_by(name=tournament_in.name).first()
    if existing:
        raise ValueError(f"Tournament '{tournament_in.name}' already exists")
    
    tournament = Tournament(**tournament_in.model_dump())
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return TournamentRead.from_orm(tournament)
```

### ❌ Incorrect

```python
def create_tournament(db, tournament_in):  # Missing type hints
    tournament = Tournament(**tournament_in.dict())
    db.add(tournament)
    db.commit()
    return tournament  # Returns ORM model, not schema
```

### Guidelines

- Use `Optional[T]` for nullable fields, never bare `None`
- Use `List[T]` instead of `list`, `Dict[K, V]` instead of `dict`
- Avoid `Any` and `**kwargs` unless absolutely necessary
- Import types from `typing` for Python 3.8-3.11 compatibility
- Use `from __future__ import annotations` for forward references

---

## 📝 Docstrings (Google Style)

All functions, classes, and methods require docstrings. Use **Google style** format.

### ✅ Complete Docstring

```python
def get_tournament_standings(
    db: Session,
    tournament_id: int,
    cache: Optional[Redis] = None,
) -> List[TeamStanding]:
    """Calculate current tournament standings with win/loss/draw statistics.
    
    Queries matches and aggregates results by team. Results are cached for
    performance optimization (TTL: 1 hour). Includes edge cases like walkovers
    and tournament stages (group/knockout).
    
    Args:
        db: Database session for queries.
        tournament_id: ID of the tournament to fetch standings for.
        cache: Optional Redis client for caching results.
    
    Returns:
        List[TeamStanding]: Teams sorted by points (descending), then by
            goal differential. Empty list if tournament has no matches yet.
    
    Raises:
        TournamentNotFound: If tournament_id doesn't exist in database.
        DatabaseError: If query fails (connection lost, corrupted data).
    
    Example:
        standings = get_tournament_standings(db, tournament_id=1)
        for team_standing in standings:
            print(f"{team_standing.team.name}: {team_standing.points} pts")
    """
```

### Docstring Checklist

- [ ] One-line summary (fits on one line)
- [ ] Blank line after summary
- [ ] Detailed description with context (edge cases, side effects)
- [ ] Args section with types and descriptions
- [ ] Returns section with type and description
- [ ] Raises section listing all possible exceptions
- [ ] Example section for complex functions (not always required)

---

## 🛡️ Exception Handling & Custom Exceptions

Create **custom exception classes** in `app/exceptions.py` for domain-specific errors.

### ✅ Custom Exceptions (Create this file)

```python
# app/exceptions.py
class TatuzinhoException(Exception):
    """Base exception for all Tatuzinho errors."""
    pass

class TournamentNotFound(TatuzinhoException):
    """Raised when a tournament is not found in the database."""
    def __init__(self, tournament_id: int):
        self.tournament_id = tournament_id
        super().__init__(f"Tournament with ID {tournament_id} not found")

class TeamNotFound(TatuzinhoException):
    """Raised when a team is not found in the database."""
    pass

class DataParsingError(TatuzinhoException):
    """Raised when external API data cannot be parsed or validated."""
    def __init__(self, api_name: str, message: str):
        super().__init__(f"Failed to parse {api_name} data: {message}")

        )

class DatabaseError(TatuzinhoException):
    """Raised for database operation failures."""
    pass
```

### ✅ Exception Usage in Services

```python
from app.exceptions import TournamentNotFound, DataParsingError

def get_tournament_by_id(db: Session, tournament_id: int) -> Tournament:
    """Fetch tournament from database, raising exception if not found."""
    tournament = db.query(Tournament).filter_by(id=tournament_id).first()
    if not tournament:
        raise TournamentNotFound(tournament_id)
    return tournament

def parse_match_data(api_response: dict) -> Match:
    """Parse external match data with validation."""
    try:
        return Match(
            source_id=api_response["id"],
            home_team_id=api_response["homeTeam"]["id"],
            away_team_id=api_response["awayTeam"]["id"],
            # ...
        )
    except KeyError as e:
        raise DataParsingError("external", f"Missing field: {e}")
    except (TypeError, ValueError) as e:
        raise DataParsingError("external", f"Invalid data type: {e}")
```

### ✅ Global Exception Handler (add to main.py)

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.exceptions import TatuzinhoException

app = FastAPI()

@app.exception_handler(TatuzinhoException)
async def tatuzinho_exception_handler(request: Request, exc: TatuzinhoException):
    """Handle all domain exceptions with consistent JSON response."""
    logger.error(f"TatuzinhoException: {exc}", extra={"url": request.url})
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "path": str(request.url.path),
        },
    )
```

### Exception Handling Rules

- **Never catch `Exception`** - be specific (`ValueError`, `KeyError`, etc.)
- **Always log before re-raising** - preserve stack traces
- **Use custom exceptions for domain errors** - not for flow control
- **Raise exceptions early** - fail fast, don't return `None`
- **Don't swallow exceptions silently** (avoid bare `except` clauses)

---

## 📊 Logging (Structured JSON)

Replace Python's built-in logging with **structured JSON logging** for better observability.

### ✅ Setup (update config.py)

```python
import json
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure structured JSON logging with rotation."""
    
    class JSONFormatter(logging.Formatter):
        def format(self, record):
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
            return json.dumps(log_obj)
    
    logger = logging.getLogger("tatuzinho")
    logger.setLevel(logging.DEBUG)
    
    # Console handler (development)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # File handler (production)
    file_handler = RotatingFileHandler(
        "logs/tatuzinho.log",
        maxBytes=10_000_000,  # 10 MB
        backupCount=5,
    )
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    return logger

# Usage
logger = setup_logging()
```

### ✅ Logging Best Practices

```python
logger.debug("Starting tournament sync", extra={"tournament_id": 123})
logger.info("Tournament created successfully", extra={"tournament_id": 123, "name": "World Cup 2022"})
logger.warning("Slow query detected", extra={"query_time_ms": 1500, "endpoint": "standings"})
logger.error("Failed to fetch external data", extra={"attempts": 3, "error": str(e)})

# ❌ Don't
logger.debug(f"Tournament: {tournament}")  # Inline variables
logger.info("Done")  # Too vague
logger.error(str(e))  # Lose stack trace
```

### Logging Rules

- Use `extra={}` dict for structured context (not f-strings)
- Log at appropriate levels: DEBUG (dev), INFO (state changes), WARNING (recoverable errors), ERROR (failures)
- **Always include relevant IDs** (tournament_id, team_id, user_id, request_id)
- **Never log sensitive data** (passwords, tokens, personal info)
- Use context managers for timing: `logger.info(f"Query took {time.time() - start:.2f}s")`

---

## ⚡ Performance & Caching

The project has Redis configured but **caching is not implemented**. Implement aggressive caching for analytics.

### ✅ Redis Caching Setup

```python
# app/cache.py
from redis import Redis
from typing import Optional, TypeVar, Callable
import json
import functools

T = TypeVar("T")

class CacheManager:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    def cache(self, key: str, ttl: int = 3600):
        """Decorator for caching function results."""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> T:
                try:
                    cached = self.redis.get(key)
                    if cached:
                        logger.debug(f"Cache hit: {key}")
                        return json.loads(cached)
                except Exception as e:
                    logger.warning(f"Cache read error: {e}")
                
                result = func(*args, **kwargs)
                
                try:
                    self.redis.setex(key, ttl, json.dumps(result, default=str))
                except Exception as e:
                    logger.warning(f"Cache write error: {e}")
                
                return result
            return wrapper
        return decorator
    
    def invalidate(self, pattern: str) -> int:
        """Invalidate cache keys matching a pattern."""
        keys = self.redis.keys(pattern)
        if keys:
            return self.redis.delete(*keys)
        return 0
```

### ✅ Apply Caching to Services

```python
# In app/services/analytics.py
def get_top_scorers(
    db: Session,
    tournament_id: int,
    cache_manager: CacheManager,
) -> List[ScorerStats]:
    """Get top goal scorers, cached for 1 hour."""
    cache_key = f"top_scorers:tournament:{tournament_id}"
    
    @cache_manager.cache(cache_key, ttl=3600)
    def _fetch():
        return db.query(Player).join(
            Goal, Goal.player_id == Player.id
        ).filter(
            Goal.tournament_id == tournament_id
        ).group_by(
            Player.id
        ).order_by(
            func.count(Goal.id).desc()
        ).limit(10).all()
    
    return _fetch()
```

### ✅ Cache Invalidation Strategy

```python
# When updating data, invalidate related caches
def update_match_result(
    db: Session,
    match_id: int,
    result: MatchResult,
    cache_manager: CacheManager,
) -> Match:
    """Update match result and invalidate dependent caches."""
    match = db.query(Match).get(match_id)
    match.home_score = result.home_score
    match.away_score = result.away_score
    db.commit()
    
    # Invalidate all caches that depend on this match
    cache_manager.invalidate(f"standings:tournament:{match.tournament_id}:*")
    cache_manager.invalidate(f"top_scorers:tournament:{match.tournament_id}")
    
    return match
```

### Caching Rules

- Cache expensive operations (aggregations, joins, external API calls)
- Set appropriate TTL (short for frequently-changing data: 15-60min, long for static: 24h)
- **Always include invalidation logic** when data changes
- **Handle cache failures gracefully** (log warning, fall back to direct query)
- Use cache keys with hierarchical structure: `resource:type:id:filter`

---

## 🗄️ Database & Queries

### ✅ Query Optimization

```python
# ❌ N+1 Problem - Multiple queries
tournaments = db.query(Tournament).all()
for tournament in tournaments:
    teams = db.query(Team).filter_by(tournament_id=tournament.id).all()  # Repeated query!

# ✅ Use join or eager loading
from sqlalchemy.orm import joinedload
tournaments = db.query(Tournament).options(
    joinedload(Tournament.teams)
).all()

# ✅ Aggregate in database, not Python
from sqlalchemy import func
scores = db.query(
    Player.id,
    Player.name,
    func.count(Goal.id).label("goal_count")
).join(
    Goal
).group_by(
    Player.id
).all()
```

### ✅ Index Strategy

Ensure models include indexes for frequently-queried fields:

```python
from sqlalchemy import Index

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    match_date = Column(DateTime, nullable=False)
    
    # Indexes on frequently-queried columns
    __table_args__ = (
        Index("ix_match_tournament_id", "tournament_id"),
        Index("ix_match_date_tournament", "match_date", "tournament_id"),
    )
```

### Database Rules

- **Use explicit joins** instead of implicit filtering
- **Index foreign keys** and date/timestamp columns
- **Use `joinedload()` or `selectinload()`** to prevent N+1 queries
- **Paginate large result sets** (use LIMIT/OFFSET)
- **Use transactions for multi-step operations**

---

## 🔗 FastAPI Router Patterns

### ✅ Clean Router Structure

```python
# app/routers/tournaments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.exceptions import TournamentNotFound
from app.services.tournament_service import TournamentService
from app.schemas import TournamentCreate, TournamentRead

router = APIRouter(prefix="/api/v1/tournaments", tags=["tournaments"])

def get_tournament_service(db: Session = Depends(get_db)) -> TournamentService:
    """Dependency injection for tournament service."""
    return TournamentService(db)

@router.post("/", response_model=TournamentRead, status_code=status.HTTP_201_CREATED)
def create_tournament(
    tournament_in: TournamentCreate,
    service: TournamentService = Depends(get_tournament_service),
) -> TournamentRead:
    """Create a new tournament."""
    try:
        return service.create(tournament_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating tournament: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{tournament_id}", response_model=TournamentRead)
def get_tournament(
    tournament_id: int,
    service: TournamentService = Depends(get_tournament_service),
) -> TournamentRead:
    """Fetch a tournament by ID."""
    try:
        return service.get_by_id(tournament_id)
    except TournamentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### Router Rules

- Keep endpoints **5-10 lines max** - delegate to services
- Use **dependency injection** for database, services, cache
- **Map exceptions to HTTP status codes**:
  - `TournamentNotFound` → 404
  - `ValueError` (validation) → 400
  - `TatuzinhoException` → 400 or 500
- Use **`response_model`** to validate and document responses
- Set appropriate **status codes** (201 for POST, 204 for DELETE, etc.)

---

## 🧪 Testing Patterns (Implement Next)

Structure tests to match architecture:

```
tests/
  unit/
    services/
      test_tournament_service.py
    repositories/
      test_tournament_repository.py
  integration/
    routers/
      test_tournaments_router.py
  conftest.py (shared fixtures)
```

### ✅ Test Example

```python
# tests/unit/services/test_tournament_service.py
import pytest
from sqlalchemy.orm import Session
from app.services.tournament_service import TournamentService
from app.exceptions import TournamentNotFound
from app.schemas import TournamentCreate

@pytest.fixture
def tournament_service(db_session: Session) -> TournamentService:
    return TournamentService(db_session)

def test_create_tournament(tournament_service: TournamentService):
    """Test creating a new tournament."""
    tournament_in = TournamentCreate(
        name="World Cup 2022",
        year=2022,
    )
    
    tournament = tournament_service.create(tournament_in)
    
    assert tournament.name == "World Cup 2022"
    assert tournament.year == 2022

def test_get_tournament_not_found(tournament_service: TournamentService):
    """Test fetching non-existent tournament raises exception."""
    with pytest.raises(TournamentNotFound):
        tournament_service.get_by_id(999)
```

---

## 🛠️ Tools & Development Setup (TODO)

To be added to `pyproject.toml` and `.pre-commit-config.yaml`:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing
- **Alembic**: Database migrations (future)

These will be implemented as part of the development workflow improvement.

---

## 📋 Checklist for Code Review

Before pushing code, verify:

- [ ] 100% type hints on all parameters and returns
- [ ] Docstring with Google style (summary, args, returns, raises)
- [ ] Custom exceptions used instead of generic `Exception`
- [ ] No direct database queries in routers
- [ ] All endpoints delegate to services
- [ ] Logging includes relevant context (IDs, status)
- [ ] N+1 queries prevented with `joinedload()` or explicit joins
- [ ] Cache invalidation implemented for data mutations
- [ ] Error handling with specific exception types
- [ ] HTTP status codes are semantically correct
- [ ] Response validated with `response_model`

---

## 🚀 Quick Reference: Layer Templates

### Service Template

```python
# app/services/{entity}_service.py
from sqlalchemy.orm import Session
from app.exceptions import TournamentNotFound
from app.schemas import TournamentRead, TournamentCreate
from app.models import Tournament

class TournamentService:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, tournament_in: TournamentCreate) -> TournamentRead:
        """Create a new tournament."""
        pass
    
    def get_by_id(self, tournament_id: int) -> TournamentRead:
        """Fetch tournament by ID or raise TournamentNotFound."""
        pass
```

### Repository Template

```python
# app/repositories/{entity}_repository.py
from sqlalchemy.orm import Session

class TournamentRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def find_by_id(self, tournament_id: int):
        """Query tournament, return None if not found."""
        pass
    
    def find_by_name(self, name: str):
        """Query tournament by name."""
        pass
```

---

## 📚 Key Files to Know

- `app/main.py` - FastAPI app initialization
- `app/config.py` - Configuration & environment
- `app/database.py` - Database connection & session
- `app/models.py` - SQLAlchemy ORM definitions
- `app/schemas.py` - Pydantic validation schemas
- `app/exceptions.py` - Custom exception classes (CREATE THIS)
- `app/cache.py` - Redis caching utilities (CREATE THIS)
- `app/services/` - Business logic layer (CREATE THIS)
- `app/repositories/` - Data access layer (CREATE THIS)

---

## ❓ Questions?

These guidelines reflect senior-level Python/FastAPI best practices as of 2024. When in doubt:

1. Check existing code patterns in routers/models
2. Refer to FastAPI docs: https://fastapi.tiangolo.com/
3. Refer to SQLAlchemy ORM: https://docs.sqlalchemy.org/
4. Reference project context: `/memories/repo/tatuzinho-project-context.md`

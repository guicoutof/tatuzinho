"""
Endpoints for match predictions.

All endpoints delegate business logic to PredictionService. This layer only
handles request validation, response formatting, and HTTP semantics.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import PredictionResponse
from app.services.prediction_service import PredictionService
from app.repositories.team import TeamRepository
from app.exceptions import TeamNotFound, DatabaseError
from app.config import logger

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


def get_prediction_service(db: Session = Depends(get_db)) -> PredictionService:
    """Dependency injection for prediction service.

    Args:
        db: Database session from dependency.

    Returns:
        PredictionService instance bound to current database session.
    """
    return PredictionService(db)


def get_team_repository(db: Session = Depends(get_db)) -> TeamRepository:
    """Dependency injection for team repository.

    Args:
        db: Database session from dependency.

    Returns:
        TeamRepository instance bound to current database session.
    """
    return TeamRepository(db)


def _resolve_team_id(
    team_id: Optional[int],
    team_name: Optional[str],
    repo: TeamRepository,
    label: str,
) -> int:
    """Resolve a team identifier to a team ID.

    Tries team_id first, then falls back to case-insensitive name lookup.

    Args:
        team_id: Team ID if provided.
        team_name: Team name if provided.
        repo: TeamRepository for database lookups.
        label: Label for error messages ("home" or "away").

    Returns:
        Resolved team ID.

    Raises:
        HTTPException: If neither or both identifiers are invalid.
    """
    if not team_id and not team_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Either {label}_team_id or {label}_team is required",
        )

    if team_id:
        return team_id

    team = repo.find_by_name(team_name)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team '{team_name}' not found",
        )
    return team.id


@router.get("/predict", response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def predict_match(
    home_team_id: Optional[int] = Query(None, description="Home team ID"),
    away_team_id: Optional[int] = Query(None, description="Away team ID"),
    home_team: Optional[str] = Query(None, description="Home team name (case-insensitive)"),
    away_team: Optional[str] = Query(None, description="Away team name (case-insensitive)"),
    service: PredictionService = Depends(get_prediction_service),
    repo: TeamRepository = Depends(get_team_repository),
) -> PredictionResponse:
    """Predict match outcome between two teams.

    Uses a Poisson distribution model based on historical match data to
    calculate home win, draw, and away win probabilities, plus the most
    likely scoreline.

    Teams can be specified by ID or by name (case-insensitive).

    Query Parameters:
        - home_team_id: Home team ID (optional if home_team provided).
        - away_team_id: Away team ID (optional if away_team provided).
        - home_team: Home team name, case-insensitive (optional if ID provided).
        - away_team: Away team name, case-insensitive (optional if ID provided).

    Returns:
        PredictionResponse with win probabilities, most likely score, and confidence.

    Raises:
        404: If one or both teams are not found.
        422: If neither ID nor name is provided for a team.
        500: If prediction calculation fails.
    """
    try:
        resolved_home = _resolve_team_id(home_team_id, home_team, repo, "home")
        resolved_away = _resolve_team_id(away_team_id, away_team, repo, "away")

        result = service.predict(resolved_home, resolved_away)

        return PredictionResponse(**result)

    except HTTPException:
        raise
    except TeamNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DatabaseError as e:
        logger.error(f"Failed to compute prediction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute prediction",
        )

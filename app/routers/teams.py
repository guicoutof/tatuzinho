"""
Endpoints for team operations.

All endpoints delegate business logic to TeamService. This layer only
handles request validation, response formatting, and HTTP semantics.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import Team as TeamSchema, TeamWithPlayers as TeamWithPlayersSchema
from app.services.team_service import TeamService
from app.exceptions import TeamNotFound, DatabaseError
from app.config import logger

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


def get_team_service(db: Session = Depends(get_db)) -> TeamService:
    """Dependency injection for team service.
    
    Args:
        db: Database session from dependency.
    
    Returns:
        TeamService instance bound to current database session.
    """
    return TeamService(db)


@router.get("/", response_model=List[TeamSchema], status_code=status.HTTP_200_OK)
async def list_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    service: TeamService = Depends(get_team_service),
) -> List[TeamSchema]:
    """List all teams with pagination.
    
    Args:
        skip: Number of records to skip for pagination (default: 0).
        limit: Maximum number of records (default: 50, max: 500).
        service: Injected TeamService instance.
    
    Returns:
        List of teams with basic information.
    
    Raises:
        500: If database query fails.
    """
    try:
        return service.get_all(skip=skip, limit=limit)
    except DatabaseError as e:
        logger.error(f"Failed to list teams: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch teams",
        )


@router.get("/{team_id}", response_model=TeamWithPlayersSchema, status_code=status.HTTP_200_OK)
async def get_team(
    team_id: int,
    service: TeamService = Depends(get_team_service),
) -> TeamWithPlayersSchema:
    """Fetch team details with roster.
    
    Returns team information including all associated players.
    
    Args:
        team_id: ID of the team.
        service: Injected TeamService instance.
    
    Returns:
        Team with players list.
    
    Raises:
        404: If team not found.
        500: If database query fails.
    """
    try:
        return service.get_with_players(team_id)
    except TeamNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to fetch team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team",
        )


@router.get("/{team_id}/analytics", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_team_analytics(
    team_id: int,
    service: TeamService = Depends(get_team_service),
) -> Dict[str, Any]:
    """Fetch team analytics from recent matches.
    
    Calculates recent form, win rate, goals per match, and possession stats
    from the last 10 finished matches.
    
    Args:
        team_id: ID of the team.
        service: Injected TeamService instance.
    
    Returns:
        Dictionary with analytics metrics including form, win rate, goal stats.
    
    Raises:
        404: If team not found.
        500: If calculation fails.
    """
    try:
        return service.get_analytics(team_id)
    except TeamNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to calculate team analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team analytics",
        )


@router.get("/{team_id}/recent-matches", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK)
async def get_team_recent_matches(
    team_id: int,
    limit: int = Query(10, ge=1, le=50),
    service: TeamService = Depends(get_team_service),
) -> List[Dict[str, Any]]:
    """Fetch recent finished matches for a team.
    
    Returns up to the specified number of finished matches, ordered by date descending.
    
    Args:
        team_id: ID of the team.
        limit: Maximum number of recent matches (default: 10, max: 50).
        service: Injected TeamService instance.
    
    Returns:
        List of recent match records with opponent, score, and result.
    
    Raises:
        404: If team not found.
        500: If query fails.
    """
    try:
        return service.get_recent_matches(team_id, limit=limit)
    except TeamNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to fetch recent matches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recent matches",
        )

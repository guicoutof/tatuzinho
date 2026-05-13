"""
Endpoints para torneios (Copa do Mundo, Eliminatórias).

All endpoints delegate business logic to TournamentService. This layer only
handles request validation, response formatting, and HTTP semantics.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import Tournament as TournamentSchema
from app.services.tournament_service import TournamentService
from app.exceptions import TournamentNotFound, DuplicateEntityError, DatabaseError
from app.config import logger

router = APIRouter(prefix="/api/v1/tournaments", tags=["tournaments"])


def get_tournament_service(db: Session = Depends(get_db)) -> TournamentService:
    """Dependency injection for tournament service.
    
    Args:
        db: Database session from dependency.
    
    Returns:
        TournamentService instance bound to current database session.
    """
    return TournamentService(db)


@router.get("/", response_model=List[TournamentSchema], status_code=status.HTTP_200_OK)
async def list_tournaments(
    skip: int = 0,
    limit: int = 100,
    service: TournamentService = Depends(get_tournament_service),
) -> List[TournamentSchema]:
    """List all available tournaments with pagination.
    
    Args:
        skip: Number of records to skip (default: 0).
        limit: Maximum number of records to return (default: 100).
        service: Injected TournamentService instance.
    
    Returns:
        List of tournaments ordered by season and type.
    
    Raises:
        500: If database query fails.
    """
    try:
        return service.get_all(skip=skip, limit=limit)
    except DatabaseError as e:
        logger.error(f"Failed to list tournaments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch tournaments",
        )


@router.get(
    "/{tournament_id}",
    response_model=TournamentSchema,
    status_code=status.HTTP_200_OK,
)
async def get_tournament(
    tournament_id: int,
    service: TournamentService = Depends(get_tournament_service),
) -> TournamentSchema:
    """Fetch tournament details by ID.
    
    Args:
        tournament_id: ID of the tournament.
        service: Injected TournamentService instance.
    
    Returns:
        Tournament with all details.
    
    Raises:
        404: If tournament not found.
        500: If database query fails.
    """
    try:
        return service.get_by_id(tournament_id)
    except TournamentNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to fetch tournament: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch tournament",
        )


@router.get(
    "/{tournament_id}/standings",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def get_standings(
    tournament_id: int,
    group: Optional[str] = None,
    service: TournamentService = Depends(get_tournament_service),
) -> List[Dict[str, Any]]:
    """Fetch tournament standings (league table).
    
    Calculates current tournament standings from finished matches. Teams are
    sorted by points (descending), then by goal difference.
    
    Args:
        tournament_id: ID of the tournament.
        group: Optional group filter (e.g., 'A', 'B' for group stage).
        service: Injected TournamentService instance.
    
    Returns:
        List of team standings with statistics, sorted by position.
    
    Raises:
        404: If tournament not found.
        500: If calculation fails.
    """
    try:
        standings = service.get_standings(tournament_id)
        
        # TODO: Implement group filtering when group stage data is available
        if group:
            logger.warning(
                f"Group filtering not yet implemented",
                extra={"group": group, "tournament_id": tournament_id},
            )
        
        return standings
    except TournamentNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to calculate standings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate standings",
        )

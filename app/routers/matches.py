"""
Endpoints for match operations.

All endpoints delegate business logic to MatchService. This layer only
handles request validation, response formatting, and HTTP semantics.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.match_service import MatchService
from app.exceptions import MatchNotFound, TournamentNotFound, DatabaseError
from app.config import logger

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


def get_match_service(db: Session = Depends(get_db)) -> MatchService:
    """Dependency injection for match service.
    
    Args:
        db: Database session from dependency.
    
    Returns:
        MatchService instance bound to current database session.
    """
    return MatchService(db)


@router.get("/", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK)
async def list_matches(
    tournament_id: Optional[int] = Query(None),
    phase: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
    match_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    service: MatchService = Depends(get_match_service),
) -> List[Dict[str, Any]]:
    """List matches with optional filters.
    
    Supports filtering by tournament, phase, group, and status. Results are
    ordered by match_date descending (most recent first).
    
    Query Parameters:
        - tournament_id: Filter by tournament ID.
        - phase: Filter by phase (group, round_of_16, quarter, semi, final).
        - group: Filter by group letter (A, B, C, etc).
        - status: Filter by match status (scheduled, inprogress, finished, cancelled).
        - skip: Pagination offset (default: 0).
        - limit: Maximum results (default: 50, max: 500).
    
    Returns:
        List of matches with scores, teams, and dates.
    
    Raises:
        500: If database query fails.
    """
    try:
        matches = service.list_with_filters(
            tournament_id=tournament_id,
            phase=phase,
            group=group,
            status=match_status,
            skip=skip,
            limit=limit,
        )
        return matches
    except DatabaseError as e:
        logger.error(f"Failed to list matches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch matches",
        )


@router.get("/{match_id}", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_match(
    match_id: int,
    service: MatchService = Depends(get_match_service),
) -> Dict[str, Any]:
    """Fetch complete match details by ID.
    
    Args:
        match_id: ID of the match.
        service: Injected MatchService instance.
    
    Returns:
        Match details including teams, score, date, and phase information.
    
    Raises:
        404: If match not found.
        500: If database query fails.
    """
    try:
        return service.get_by_id(match_id)
    except MatchNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to fetch match: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch match",
        )


@router.get("/{match_id}/statistics", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_match_statistics(
    match_id: int,
    service: MatchService = Depends(get_match_service),
) -> Dict[str, Any]:
    """Fetch detailed match statistics.
    
    Returns possession, shots, passes, tackles, fouls, and other metrics
    for both teams in the match.
    
    Args:
        match_id: ID of the match.
        service: Injected MatchService instance.
    
    Returns:
        Dictionary with home and away team statistics.
    
    Raises:
        404: If match not found.
        500: If database query fails.
    """
    try:
        return service.get_statistics(match_id)
    except MatchNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to fetch match statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch match statistics",
        )


@router.post("/sync/{tournament_id}", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def trigger_match_sync(
    tournament_id: int,
    start_date: str = Query(...),
    end_date: str = Query(...),
    service: MatchService = Depends(get_match_service),
) -> Dict[str, Any]:
    """Trigger manual synchronization of matches from SofaScore API.
    
    This is an administrative endpoint for manual syncs. For automatic
    synchronization, use Celery background tasks.
    
    Query Parameters:
        - start_date: Start date for sync period (YYYY-MM-DD format).
        - end_date: End date for sync period (YYYY-MM-DD format).
    
    Returns:
        Status dict with sync operation details.
    
    Raises:
        404: If tournament not found.
        400: If date format is invalid.
        500: If sync fails.
    """
    try:
        # Parse dates
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD",
            )
        
        return service.trigger_sync(tournament_id, parsed_start, parsed_end)
    
    except TournamentNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to trigger match sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger synchronization",
        )

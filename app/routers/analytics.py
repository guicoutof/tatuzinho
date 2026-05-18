"""
Endpoints for analytics operations.

All endpoints delegate business logic to AnalyticsService. This layer only
handles request validation, response formatting, and HTTP semantics.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics_service import AnalyticsService
from app.exceptions import TournamentNotFound, TeamNotFound, DatabaseError
from app.config import logger

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    """Dependency injection for analytics service.
    
    Args:
        db: Database session from dependency.
    
    Returns:
        AnalyticsService instance bound to current database session.
    """
    return AnalyticsService(db)


@router.get("/top-scorers", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK)
async def get_top_scorers(
    tournament_id: int = Query(..., description="Tournament ID"),
    limit: int = Query(10, ge=1, le=100),
    service: AnalyticsService = Depends(get_analytics_service),
) -> List[Dict[str, Any]]:
    """Get top goal scorers in a tournament.
    
    Returns players ranked by total goals scored in all matches of the tournament.
    Results should be cached for performance (1 hour TTL recommended).
    
    Query Parameters:
        - tournament_id: Tournament ID (required).
        - limit: Maximum number of scorers (default: 10, max: 100).
    
    Returns:
        List of scorers with name, team, position, and total goals.
    
    Raises:
        404: If tournament not found.
        500: If query fails.
    """
    try:
        return service.get_top_scorers(tournament_id, limit=limit)
    except TournamentNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to fetch top scorers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch top scorers",
        )


@router.get("/top-assistants", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK)
async def get_top_assistants(
    tournament_id: int = Query(..., description="Tournament ID"),
    limit: int = Query(10, ge=1, le=100),
    service: AnalyticsService = Depends(get_analytics_service),
) -> List[Dict[str, Any]]:
    """Get top assist providers in a tournament.
    
    Returns players ranked by total assists provided in all matches of the tournament.
    Results should be cached for performance (1 hour TTL recommended).
    
    Query Parameters:
        - tournament_id: Tournament ID (required).
        - limit: Maximum number of assistants (default: 10, max: 100).
    
    Returns:
        List of assistants with name, team, position, and total assists.
    
    Raises:
        404: If tournament not found.
        500: If query fails.
    """
    try:
        return service.get_top_assistants(tournament_id, limit=limit)
    except TournamentNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to fetch top assistants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch top assistants",
        )


@router.get("/tournaments/{tournament_id}/summary", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_tournament_summary(
    tournament_id: int,
    service: AnalyticsService = Depends(get_analytics_service),
) -> Dict[str, Any]:
    """Get comprehensive tournament summary.
    
    Returns aggregate statistics including total matches, goals, teams, and leaders.
    Results should be cached for performance (1 hour TTL recommended).
    
    Args:
        tournament_id: ID of the tournament.
        service: Injected AnalyticsService instance.
    
    Returns:
        Dictionary with tournament statistics and leaders (top scorer, top assistant).
    
    Raises:
        404: If tournament not found.
        500: If calculation fails.
    """
    try:
        return service.get_tournament_summary(tournament_id)
    except TournamentNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to fetch tournament summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch tournament summary",
        )


@router.get("/comparison/{team1_id}/{team2_id}", status_code=status.HTTP_200_OK)
async def compare_teams(
    team1_id: int,
    team2_id: int,
    tournament_id: Optional[int] = Query(None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> Dict[str, Any]:
    """Compara dois times head-to-head.

    Retorna histórico de confrontos diretos entre duas seleções/times,
    incluindo vitórias, derrotas, empates e lista de partidas.

    Args:
        team1_id: ID do primeiro time.
        team2_id: ID do segundo time.
        tournament_id: Opcional, filtrar por torneio específico.
        service: Injected AnalyticsService instance.

    Returns:
        Dicionário com histórico de confrontos, estatísticas e lista de partidas.

    Raises:
        404: Se um ou ambos os times não forem encontrados.
    """
    try:
        return service.compare_teams(team1_id, team2_id, tournament_id)
    except TeamNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to compare teams: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare teams",
        )

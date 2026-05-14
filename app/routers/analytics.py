"""
Endpoints for analytics operations.

All endpoints delegate business logic to AnalyticsService. This layer only
handles request validation, response formatting, and HTTP semantics.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics_service import AnalyticsService
from app.exceptions import TournamentNotFound, DatabaseError
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
    
    return {
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        "total_matches": total_matches,
        "finished_matches": finished_matches,
        "total_goals": total_goals_sum,
        "average_goals_per_match": avg_goals_per_match,
        "participating_teams": participating_teams,
    }


@router.get("/comparison/{team1_id}/{team2_id}")
def compare_teams(
    team1_id: int,
    team2_id: int,
    tournament_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Compara dois times"""
    team1 = db.query(models.Team).filter(models.Team.id == team1_id).first()
    team2 = db.query(models.Team).filter(models.Team.id == team2_id).first()
    
    if not team1 or not team2:
        raise HTTPException(status_code=404, detail="One or both teams not found")
    
    # Buscar histórico entre os dois times
    head_to_head = db.query(models.Match).filter(
        ((models.Match.home_team_id == team1_id) & (models.Match.away_team_id == team2_id)) |
        ((models.Match.home_team_id == team2_id) & (models.Match.away_team_id == team1_id)),
        models.Match.status == "finished"
    )
    
    if tournament_id:
        head_to_head = head_to_head.filter(models.Match.tournament_id == tournament_id)
    
    h2h_matches = head_to_head.all()
    
    team1_wins = 0
    team2_wins = 0
    draws = 0
    
    for match in h2h_matches:
        if match.home_team_id == team1_id:
            if match.home_score > match.away_score:
                team1_wins += 1
            elif match.away_score > match.home_score:
                team2_wins += 1
            else:
                draws += 1
        else:
            if match.away_score > match.home_score:
                team1_wins += 1
            elif match.home_score > match.away_score:
                team2_wins += 1
            else:
                draws += 1
    
    return {
        "team1": {
            "id": team1.id,
            "name": team1.name,
            "wins": team1_wins,
        },
        "team2": {
            "id": team2.id,
            "name": team2.name,
            "wins": team2_wins,
        },
        "draws": draws,
        "total_matches": len(h2h_matches),
        "head_to_head": [
            {
                "date": m.match_date,
                "home": m.home_team.name,
                "away": m.away_team.name,
                "score": f"{m.home_score} - {m.away_score}",
            }
            for m in h2h_matches
        ]
    }

"""
Endpoints para partidas
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


@router.get("/", response_model=List[schemas.MatchWithDetails])
def list_matches(
    tournament_id: Optional[int] = Query(None),
    phase: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Lista partidas com filtros opcionais
    
    Query params:
        - tournament_id: Filtrar por torneio
        - phase: Filtrar por fase (group, round_of_16, quarter, semi, final)
        - group: Filtrar por grupo (A, B, C, etc)
        - status: Filtrar por status (scheduled, inprogress, finished, cancelled)
    """
    query = db.query(models.Match)
    
    if tournament_id:
        query = query.filter(models.Match.tournament_id == tournament_id)
    
    if phase:
        query = query.filter(models.Match.phase == phase)
    
    if group:
        query = query.filter(models.Match.group == group)
    
    if status:
        query = query.filter(models.Match.status == status)
    
    matches = query.order_by(models.Match.match_date.desc()).offset(skip).limit(limit).all()
    return matches


@router.get("/{match_id}", response_model=schemas.MatchWithDetails)
def get_match(match_id: int, db: Session = Depends(get_db)):
    """Obtém detalhes completos de uma partida"""
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    return match


@router.get("/{match_id}/statistics")
def get_match_statistics(match_id: int, db: Session = Depends(get_db)):
    """Obtém estatísticas detalhadas de uma partida"""
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    stats = db.query(models.MatchStatistic).filter(
        models.MatchStatistic.match_id == match_id
    ).all()
    
    # Agrupar por time
    result = {
        "match_id": match_id,
        "home_team": match.home_team.name,
        "away_team": match.away_team.name,
        "home_stats": None,
        "away_stats": None,
    }
    
    for stat in stats:
        if stat.team_id == match.home_team_id:
            result["home_stats"] = {
                "possession": stat.possession,
                "shots": stat.shots,
                "shots_on_target": stat.shots_on_target,
                "passes": stat.passes,
                "pass_accuracy": stat.pass_accuracy,
                "tackles": stat.tackles,
                "interceptions": stat.interceptions,
                "fouls": stat.fouls,
                "offsides": stat.offsides,
                "corners": stat.corners,
            }
        elif stat.team_id == match.away_team_id:
            result["away_stats"] = {
                "possession": stat.possession,
                "shots": stat.shots,
                "shots_on_target": stat.shots_on_target,
                "passes": stat.passes,
                "pass_accuracy": stat.pass_accuracy,
                "tackles": stat.tackles,
                "interceptions": stat.interceptions,
                "fouls": stat.fouls,
                "offsides": stat.offsides,
                "corners": stat.corners,
            }
    
    return result


@router.post("/sync/{tournament_id}")
def trigger_match_sync(
    tournament_id: int,
    start_date: str = Query(...),  # YYYY-MM-DD
    end_date: str = Query(...),    # YYYY-MM-DD
    db: Session = Depends(get_db)
):
    """
    Força sincronização de partidas do SofaScore
    
    Query params:
        - start_date: Data inicial (YYYY-MM-DD)
        - end_date: Data final (YYYY-MM-DD)
    
    Nota: Este é um endpoint manual. Para sincronização automática,
    use as tasks Celery.
    """
    from app.data_parser import sync_tournament_matches
    
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    try:
        sync_tournament_matches(db, tournament_id, start, end)
        return {
            "status": "success",
            "message": f"Sincronização iniciada para torneio {tournament_id}",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )

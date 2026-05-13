"""
Endpoints para times (seleções)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


@router.get("/", response_model=List[schemas.Team])
def list_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Lista todos os times"""
    teams = db.query(models.Team).offset(skip).limit(limit).all()
    return teams


@router.get("/{team_id}", response_model=schemas.TeamWithPlayers)
def get_team(team_id: int, db: Session = Depends(get_db)):
    """Obtém detalhes de um time com seu elenco"""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return team


@router.get("/{team_id}/analytics", response_model=schemas.TeamAnalytics)
def get_team_analytics(team_id: int, db: Session = Depends(get_db)):
    """Obtém análises de um time (forma, taxa vitória, etc)"""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Buscar últimos 10 jogos
    recent_matches = db.query(models.Match).filter(
        (models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id),
        models.Match.status == "finished"
    ).order_by(models.Match.match_date.desc()).limit(10).all()
    
    # Calcular estatísticas
    total_matches = len(recent_matches)
    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0
    possession_values = []
    
    recent_form = []
    
    for match in recent_matches:
        if match.home_team_id == team_id:
            goals_for += match.home_score or 0
            goals_against += match.away_score or 0
            
            if match.home_score > match.away_score:
                wins += 1
                recent_form.insert(0, "W")
            elif match.home_score == match.away_score:
                draws += 1
                recent_form.insert(0, "D")
            else:
                losses += 1
                recent_form.insert(0, "L")
        else:
            goals_for += match.away_score or 0
            goals_against += match.home_score or 0
            
            if match.away_score > match.home_score:
                wins += 1
                recent_form.insert(0, "W")
            elif match.away_score == match.home_score:
                draws += 1
                recent_form.insert(0, "D")
            else:
                losses += 1
                recent_form.insert(0, "L")
        
        # Possession
        stat = db.query(models.MatchStatistic).filter(
            models.MatchStatistic.match_id == match.id,
            models.MatchStatistic.team_id == team_id,
        ).first()
        
        if stat and stat.possession:
            possession_values.append(stat.possession)
    
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
    avg_goals_for = (goals_for / total_matches) if total_matches > 0 else 0
    avg_goals_against = (goals_against / total_matches) if total_matches > 0 else 0
    avg_possession = (sum(possession_values) / len(possession_values)) if possession_values else None
    
    # Top scorers do time
    top_scorers = db.query(models.Player).filter(
        models.Player.team_id == team_id
    ).order_by(models.Player.goals.desc()).limit(5).all()
    
    return schemas.TeamAnalytics(
        team=team,
        recent_form=recent_form,
        win_rate=win_rate,
        average_goals_for=avg_goals_for,
        average_goals_against=avg_goals_against,
        average_possession=avg_possession,
        top_scorers=top_scorers,
    )


@router.get("/{team_id}/players", response_model=List[schemas.Player])
def get_team_players(team_id: int, db: Session = Depends(get_db)):
    """Lista jogadores de um time"""
    players = db.query(models.Player).filter(
        models.Player.team_id == team_id
    ).all()
    
    if not players:
        raise HTTPException(status_code=404, detail="Team has no players")
    
    return players


@router.get("/by-code/{code}", response_model=schemas.Team)
def get_team_by_code(code: str, db: Session = Depends(get_db)):
    """Obtém time pelo código (ex: 'BRA' para Brasil)"""
    team = db.query(models.Team).filter(
        models.Team.code.ilike(code)
    ).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return team

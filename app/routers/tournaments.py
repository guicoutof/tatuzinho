"""
Endpoints para torneios (Copa do Mundo, Eliminatórias)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/v1/tournaments", tags=["tournaments"])


@router.get("/", response_model=List[schemas.Tournament])
def list_tournaments(db: Session = Depends(get_db)):
    """Lista todos os torneios disponíveis"""
    tournaments = db.query(models.Tournament).all()
    return tournaments


@router.get("/{tournament_id}", response_model=schemas.Tournament)
def get_tournament(tournament_id: int, db: Session = Depends(get_db)):
    """Obtém detalhes de um torneio"""
    tournament = db.query(models.Tournament).filter(
        models.Tournament.id == tournament_id
    ).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    return tournament


@router.get("/{tournament_id}/standings", response_model=List[schemas.TournamentStanding])
def get_standings(
    tournament_id: int, 
    group: str = None,
    db: Session = Depends(get_db)
):
    """
    Obtém a tabela (standings) de um torneio
    
    Args:
        tournament_id: ID do torneio
        group: Opcional, filtrar por grupo (ex: 'A', 'B')
    
    Returns:
        Lista de times ordenados por pontos
    """
    tournament = db.query(models.Tournament).filter(
        models.Tournament.id == tournament_id
    ).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Buscar matches do torneio
    query = db.query(models.Match).filter(
        models.Match.tournament_id == tournament_id,
        models.Match.status == "finished"
    )
    
    if group:
        query = query.filter(models.Match.group == group)
    
    matches = query.all()
    
    # Calcular estatísticas por time
    team_stats = {}
    
    for match in matches:
        for team_id, score, opponent_score in [
            (match.home_team_id, match.home_score, match.away_score),
            (match.away_team_id, match.away_score, match.home_score),
        ]:
            if team_id not in team_stats:
                team = db.query(models.Team).filter(models.Team.id == team_id).first()
                team_stats[team_id] = {
                    "team": team,
                    "matches": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "gf": 0,
                    "ga": 0,
                }
            
            team_stats[team_id]["matches"] += 1
            team_stats[team_id]["gf"] += score or 0
            team_stats[team_id]["ga"] += opponent_score or 0
            
            if score > opponent_score:
                team_stats[team_id]["wins"] += 1
            elif score == opponent_score:
                team_stats[team_id]["draws"] += 1
            else:
                team_stats[team_id]["losses"] += 1
    
    # Converter para standings
    standings = []
    for pos, (team_id, stats) in enumerate(sorted(
        team_stats.items(),
        key=lambda x: (
            -(x[1]["wins"] * 3 + x[1]["draws"]),
            -(x[1]["gf"] - x[1]["ga"]),
            -x[1]["gf"]
        ),
        reverse=False
    ), 1):
        standing = schemas.TournamentStanding(
            position=pos,
            team=stats["team"],
            matches_played=stats["matches"],
            wins=stats["wins"],
            draws=stats["draws"],
            losses=stats["losses"],
            goals_for=stats["gf"],
            goals_against=stats["ga"],
            goal_difference=stats["gf"] - stats["ga"],
            points=stats["wins"] * 3 + stats["draws"],
        )
        standings.append(standing)
    
    return standings

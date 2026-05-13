"""
Endpoints para análises e previsões
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/top-scorers", response_model=schemas.TopScorersResponse)
def get_top_scorers(
    tournament_id: int = Query(...),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Obtém artilheiros de um torneio"""
    tournament = db.query(models.Tournament).filter(
        models.Tournament.id == tournament_id
    ).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Buscar jogadores que participaram do torneio
    scorers = db.query(models.Player).join(
        models.MatchStatistic,
        models.MatchStatistic.player_id == models.Player.id
    ).join(
        models.Match,
        models.Match.id == models.MatchStatistic.match_id
    ).filter(
        models.Match.tournament_id == tournament_id,
        models.MatchStatistic.goals > 0
    ).order_by(models.MatchStatistic.goals.desc()).distinct().limit(limit).all()
    
    return schemas.TopScorersResponse(
        tournament_id=tournament_id,
        scorers=scorers,
    )


@router.get("/top-assistants", response_model=List[schemas.Player])
def get_top_assistants(
    tournament_id: int = Query(...),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Obtém melhores assistentes de um torneio"""
    tournament = db.query(models.Tournament).filter(
        models.Tournament.id == tournament_id
    ).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Buscar jogadores com mais assistências
    assistants = db.query(models.Player).join(
        models.MatchStatistic,
        models.MatchStatistic.player_id == models.Player.id
    ).join(
        models.Match,
        models.Match.id == models.MatchStatistic.match_id
    ).filter(
        models.Match.tournament_id == tournament_id,
        models.MatchStatistic.assists > 0
    ).order_by(models.MatchStatistic.assists.desc()).distinct().limit(limit).all()
    
    return assistants


@router.get("/tournament/{tournament_id}/summary")
def get_tournament_summary(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    """Obtém resumo geral de um torneio"""
    tournament = db.query(models.Tournament).filter(
        models.Tournament.id == tournament_id
    ).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Contar partidas
    total_matches = db.query(models.Match).filter(
        models.Match.tournament_id == tournament_id
    ).count()
    
    finished_matches = db.query(models.Match).filter(
        models.Match.tournament_id == tournament_id,
        models.Match.status == "finished"
    ).count()
    
    # Total de gols
    total_goals = db.query(
        models.Match
    ).filter(
        models.Match.tournament_id == tournament_id,
        models.Match.status == "finished"
    ).with_entities(
        (models.Match.home_score + models.Match.away_score).label("total")
    )
    
    total_goals_sum = sum([g[0] for g in total_goals.all() if g[0]])
    
    # Times participantes
    participating_teams = db.query(models.Team).join(
        models.Match,
        (models.Match.home_team_id == models.Team.id) | 
        (models.Match.away_team_id == models.Team.id)
    ).filter(
        models.Match.tournament_id == tournament_id
    ).distinct().count()
    
    avg_goals_per_match = (total_goals_sum / finished_matches) if finished_matches > 0 else 0
    
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

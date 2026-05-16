"""
Parser para normalizar dados do SofaScore para os modelos locais.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app import models, schemas
from app.sofascore_client import SofaScoreClient

logger = logging.getLogger(__name__)


class SofaScoreDataParser:
    """Converte dados SofaScore em models SQLAlchemy"""
    
    def __init__(self, db: Session):
        self.db = db
        self.client = SofaScoreClient()
    
    # ============ Tournament Parsing ============
    
    def parse_tournament(self, sofascore_data: Dict[str, Any]) -> models.Tournament:
        """Converte dados SofaScore de torneio para Tournament model"""
        
        # Buscar ou criar
        existing = self.db.query(models.Tournament).filter(
            models.Tournament.source_id == str(sofascore_data["id"]),
            models.Tournament.source == "sofascore",
        ).first()
        
        if existing:
            return existing
        
        # Detectar tipo
        name = sofascore_data.get("name", "")
        tournament_type = "worldcup" if "world cup" in name.lower() else "qualifier"
        
        # Extrair season
        season = sofascore_data.get("season", {}).get("year", 2026)
        
        tournament = models.Tournament(
            source_id=str(sofascore_data["id"]),
            source="sofascore",
            name=name,
            slug=sofascore_data.get("slug", ""),
            season=season,
            type=tournament_type,
            country=sofascore_data.get("country", {}).get("name"),
            start_date=self._parse_datetime(sofascore_data.get("startDate")),
            end_date=self._parse_datetime(sofascore_data.get("endDate")),
        )
        
        self.db.add(tournament)
        self.db.commit()
        return tournament
    
    # ============ Team Parsing ============
    
    def parse_team(self, sofascore_data: Dict[str, Any]) -> models.Team:
        """Converte dados SofaScore de time para Team model"""
        
        # Buscar ou criar
        existing = self.db.query(models.Team).filter(
            models.Team.source_id == sofascore_data["id"],
            models.Team.source == "sofascore",
        ).first()
        
        if existing:
            return existing
        
        team = models.Team(
            source_id=sofascore_data["id"],
            source="sofascore",
            name=sofascore_data.get("name", ""),
            code=sofascore_data.get("alpha2", sofascore_data.get("name", "")[:3].upper()),
            country=sofascore_data.get("country", {}).get("name", ""),
            logo_url=sofascore_data.get("logo", {}).get("url") if sofascore_data.get("logo") else None,
        )
        
        self.db.add(team)
        self.db.commit()
        return team
    
    def update_team_stats(self, team: models.Team, stats_data: Dict[str, Any]):
        """Atualiza estatísticas agregadas do time"""
        team.matches_played = stats_data.get("matches", 0)
        team.wins = stats_data.get("wins", 0)
        team.draws = stats_data.get("draws", 0)
        team.losses = stats_data.get("losses", 0)
        team.goals_for = stats_data.get("goalsFor", 0)
        team.goals_against = stats_data.get("goalsAgainst", 0)
        team.goal_difference = stats_data.get("goalDifference", 0)
        team.points = stats_data.get("points", 0)
        self.db.commit()
    
    # ============ Player Parsing ============
    
    def parse_player(self, sofascore_data: Dict[str, Any], team_id: Optional[int] = None) -> models.Player:
        """Converte dados SofaScore de jogador para Player model"""
        
        # Buscar ou criar
        existing = self.db.query(models.Player).filter(
            models.Player.source_id == sofascore_data["id"],
            models.Player.source == "sofascore",
        ).first()
        
        if existing:
            return existing
        
        # Determinar posição
        position_map = {
            "G": "GK",  # Goalkeeper
            "D": "DEF",  # Defender
            "M": "MID",  # Midfielder
            "F": "FWD",  # Forward
        }
        
        raw_position = sofascore_data.get("position", "M")
        position = position_map.get(raw_position, "MID")
        
        player = models.Player(
            source_id=sofascore_data["id"],
            source="sofascore",
            name=sofascore_data.get("name", ""),
            position=position,
            number=sofascore_data.get("shirtNumber"),
            birth_date=self._parse_datetime(sofascore_data.get("dateOfBirth")),
            nationality=sofascore_data.get("country", {}).get("name"),
            height=sofascore_data.get("height"),
            team_id=team_id,
        )
        
        self.db.add(player)
        self.db.commit()
        return player
    
    # ============ Match Parsing ============
    
    def parse_match(
        self, 
        sofascore_data: Dict[str, Any],
        tournament_id: int
    ) -> models.Match:
        """Converte dados SofaScore de partida para Match model"""
        
        # Buscar ou criar
        existing = self.db.query(models.Match).filter(
            models.Match.source_id == sofascore_data["id"],
            models.Match.source == "sofascore",
        ).first()
        
        if existing:
            return existing
        
        # Parse times
        home_team_data = sofascore_data.get("homeTeam", {})
        away_team_data = sofascore_data.get("awayTeam", {})
        
        home_team = self.parse_team(home_team_data)
        away_team = self.parse_team(away_team_data)
        
        # Parse scores
        home_score = sofascore_data.get("homeScore", {}).get("current")
        away_score = sofascore_data.get("awayScore", {}).get("current")
        home_score_ht = sofascore_data.get("homeScore", {}).get("period1")
        away_score_ht = sofascore_data.get("awayScore", {}).get("period1")
        
        # Status
        status_map = {
            "scheduled": "scheduled",
            "inprogress": "inprogress",
            "finished": "finished",
            "canceled": "cancelled",
        }
        status = status_map.get(sofascore_data.get("status"), "scheduled")
        
        # Fase/Grupo
        group = sofascore_data.get("group")
        phase = None
        if sofascore_data.get("isRound"):
            phase_name = sofascore_data.get("roundInfo", {}).get("name", "")
            phase = self._map_phase(phase_name)
        
        match = models.Match(
            source_id=sofascore_data["id"],
            source="sofascore",
            tournament_id=tournament_id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=self._parse_datetime(sofascore_data.get("startTimestamp")),
            status=status,
            home_score=home_score,
            away_score=away_score,
            home_score_ht=home_score_ht,
            away_score_ht=away_score_ht,
            group=group,
            phase=phase,
            venue=sofascore_data.get("venue", {}).get("name"),
            city=sofascore_data.get("venue", {}).get("city", {}).get("name"),
            attendance=sofascore_data.get("attendance"),
        )
        
        self.db.add(match)
        self.db.commit()
        return match
    
    # ============ Match Statistics Parsing ============
    
    def parse_match_statistics(
        self, 
        match: models.Match,
        sofascore_stats: Dict[str, Any]
    ):
        """Converte estatísticas do SofaScore para MatchStatistic"""
        
        # Limpar stats antigos
        self.db.query(models.MatchStatistic).filter(
            models.MatchStatistic.match_id == match.id
        ).delete()
        
        # Paraser stats por time
        for team_key in ["home", "away"]:
            if team_key not in sofascore_stats:
                continue
            
            team_id = match.home_team_id if team_key == "home" else match.away_team_id
            team_stats = sofascore_stats[team_key]
            
            stat = models.MatchStatistic(
                match_id=match.id,
                team_id=team_id,
                possession=team_stats.get("possession"),
                shots=team_stats.get("shots", 0),
                shots_on_target=team_stats.get("shotsOnTarget", 0),
                passes=team_stats.get("passes", 0),
                pass_accuracy=team_stats.get("passAccuracy"),
                tackles=team_stats.get("tackles", 0),
                interceptions=team_stats.get("interceptions", 0),
                fouls=team_stats.get("fouls", 0),
                offsides=team_stats.get("offsides", 0),
                corners=team_stats.get("corners", 0),
            )
            
            self.db.add(stat)
        
        self.db.commit()
    
    # ============ Helper Methods ============
    
    @staticmethod
    def _parse_datetime(timestamp: Optional[Any]) -> Optional[datetime]:
        """Converte timestamp UNIX para datetime"""
        if timestamp is None:
            return None
        
        try:
            if isinstance(timestamp, int):
                return datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except (ValueError, OSError):
            logger.warning(f"Could not parse timestamp: {timestamp}")
        
        return None
    
    @staticmethod
    def _map_phase(phase_name: str) -> Optional[str]:
        """Mapeia nome da fase para código interno"""
        phase_name = phase_name.lower()
        
        mapping = {
            "group": "group",
            "groups": "group",
            "round of 16": "round_of_16",
            "round of 32": "round_of_32",
            "quarterfinal": "quarter",
            "semifinal": "semi",
            "final": "final",
            "third place": "third_place",
            "playoff": "playoff",
            "qualifying": "qualifier",
        }
        
        for key, value in mapping.items():
            if key in phase_name:
                return value
        
        return None


def sync_tournament_matches(
    db: Session, 
    tournament_source_id: str,
    start_date: datetime,
    end_date: datetime
):
    """
    Sincroniza todas as partidas de um torneio em um intervalo de datas
    
    Args:
        db: Sessão do banco
        tournament_source_id: ID do torneio no SofaScore
        start_date: Data inicial
        end_date: Data final
    """
    parser = SofaScoreDataParser(db)
    client = SofaScoreClient()
    
    logger.info(f"Sincronizando torneio {tournament_source_id} de {start_date} a {end_date}")
    
    # Buscar torneio localmente
    tournament = db.query(models.Tournament).filter(
        models.Tournament.source_id == tournament_source_id,
        models.Tournament.source == "sofascore",
    ).first()
    
    if not tournament:
        logger.error(f"Tournament {tournament_source_id} not found in database")
        return
    
    # Buscar partidas no intervalo
    matches_data = client.get_matches_date_range(start_date, end_date)
    
    logger.info(f"Encontradas {len(matches_data)} partidas no intervalo")
    
    for match_data in matches_data:
        # Filtrar apenas partidas do torneio
        if match_data.get("tournament", {}).get("id") != int(tournament_source_id):
            continue
        
        try:
            # Parse match
            match = parser.parse_match(match_data, tournament.id)
            
            # Se partida terminada, buscar stats detalhadas
            if match.status == "finished":
                event_detail = client.get_event(match.source_id)
                if event_detail:
                    stats = client.get_event_statistics(match.source_id)
                    if stats:
                        parser.parse_match_statistics(match, stats)
            
            logger.debug(f"✓ Sincronizada partida {match.id}")
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar partida {match_data.get('id')}: {e}")
            continue

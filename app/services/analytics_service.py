"""
Service layer for analytics operations.

Handles analytics queries like top scorers, top assistants, tournament summaries.
Most analytics operations are read-heavy and benefit from caching.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models import Player, Match, MatchStatistic, Tournament, Team
from app.exceptions import TournamentNotFound, TeamNotFound, DatabaseError
from app.services import BaseService
from app.config import logger


class AnalyticsService(BaseService):
    """Service for analytics operations.
    
    Handles read-heavy analytics queries for insights into tournaments,
    players, and teams. Results benefit from caching.
    """
    
    def get_top_scorers(
        self,
        tournament_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top goal scorers in a tournament.
        
        Aggregates goals from MatchStatistic for all players in tournament matches.
        Results should be cached (1 hour TTL recommended).
        
        Args:
            tournament_id: ID of the tournament.
            limit: Maximum number of scorers to return (default: 10).
        
        Returns:
            List of scorers with goals, teams, and positions.
        
        Raises:
            TournamentNotFound: If tournament doesn't exist.
        """
        try:
            # Verify tournament exists
            tournament = self.db.query(Tournament).filter_by(
                id=tournament_id
            ).first()
            
            if not tournament:
                raise TournamentNotFound(tournament_id)
            
            # Query top scorers with aggregation
            scorers = self.db.query(
                Player.id,
                Player.name,
                Player.position,
                Team.name.label("team_name"),
                Team.code.label("team_code"),
                func.sum(MatchStatistic.goals).label("total_goals"),
            ).join(
                Team, Player.team_id == Team.id
            ).join(
                MatchStatistic, Player.id == MatchStatistic.player_id
            ).join(
                Match, MatchStatistic.match_id == Match.id
            ).filter(
                Match.tournament_id == tournament_id,
                MatchStatistic.goals > 0,
            ).group_by(
                Player.id, Player.name, Player.position,
                Team.id, Team.name, Team.code
            ).order_by(
                func.sum(MatchStatistic.goals).desc()
            ).limit(limit).all()
            
            result = []
            for scorer in scorers:
                result.append({
                    "player_id": scorer.id,
                    "name": scorer.name,
                    "position": scorer.position,
                    "team_name": scorer.team_name,
                    "team_code": scorer.team_code,
                    "goals": scorer.total_goals or 0,
                })
            
            logger.debug(
                f"Top scorers fetched",
                extra={"tournament_id": tournament_id, "count": len(result)}
            )
            
            return result
        
        except TournamentNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to fetch top scorers",
                extra={"tournament_id": tournament_id, "error": str(e)}
            )
            raise DatabaseError("get_top_scorers", str(e))
    
    def get_top_assistants(
        self,
        tournament_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top assist providers in a tournament.
        
        Aggregates assists from MatchStatistic for all players in tournament matches.
        Results should be cached (1 hour TTL recommended).
        
        Args:
            tournament_id: ID of the tournament.
            limit: Maximum number of players to return (default: 10).
        
        Returns:
            List of assistants with assists, teams, and positions.
        
        Raises:
            TournamentNotFound: If tournament doesn't exist.
        """
        try:
            # Verify tournament exists
            tournament = self.db.query(Tournament).filter_by(
                id=tournament_id
            ).first()
            
            if not tournament:
                raise TournamentNotFound(tournament_id)
            
            # Query top assistants with aggregation
            assistants = self.db.query(
                Player.id,
                Player.name,
                Player.position,
                Team.name.label("team_name"),
                Team.code.label("team_code"),
                func.sum(MatchStatistic.assists).label("total_assists"),
            ).join(
                Team, Player.team_id == Team.id
            ).join(
                MatchStatistic, Player.id == MatchStatistic.player_id
            ).join(
                Match, MatchStatistic.match_id == Match.id
            ).filter(
                Match.tournament_id == tournament_id,
                MatchStatistic.assists > 0,
            ).group_by(
                Player.id, Player.name, Player.position,
                Team.id, Team.name, Team.code
            ).order_by(
                func.sum(MatchStatistic.assists).desc()
            ).limit(limit).all()
            
            result = []
            for assistant in assistants:
                result.append({
                    "player_id": assistant.id,
                    "name": assistant.name,
                    "position": assistant.position,
                    "team_name": assistant.team_name,
                    "team_code": assistant.team_code,
                    "assists": assistant.total_assists or 0,
                })
            
            logger.debug(
                f"Top assistants fetched",
                extra={"tournament_id": tournament_id, "count": len(result)}
            )
            
            return result
        
        except TournamentNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to fetch top assistants",
                extra={"tournament_id": tournament_id, "error": str(e)}
            )
            raise DatabaseError("get_top_assistants", str(e))
    
    def get_tournament_summary(
        self,
        tournament_id: int,
    ) -> Dict[str, Any]:
        """Get comprehensive summary of a tournament.
        
        Includes:
        - Total matches played
        - Total goals scored
        - Average goals per match
        - Participating teams count
        - Top scorer and assistant
        
        Args:
            tournament_id: ID of the tournament.
        
        Returns:
            Dictionary with tournament summary statistics.
        
        Raises:
            TournamentNotFound: If tournament doesn't exist.
        """
        try:
            # Verify tournament exists
            tournament = self.db.query(Tournament).filter_by(
                id=tournament_id
            ).first()
            
            if not tournament:
                raise TournamentNotFound(tournament_id)
            
            # Count matches
            total_matches = self.db.query(Match).filter(
                Match.tournament_id == tournament_id,
                Match.status == "finished",
            ).count()
            
            # Count teams
            total_teams = self.db.query(Team).join(
                Team.tournaments
            ).filter(
                Tournament.id == tournament_id
            ).count()
            
            # Calculate total goals
            total_goals_result = self.db.query(
                func.sum(MatchStatistic.goals)
            ).join(
                Match, MatchStatistic.match_id == Match.id
            ).filter(
                Match.tournament_id == tournament_id
            ).scalar()
            
            total_goals = total_goals_result or 0
            
            # Get top scorer
            top_scorer = self.get_top_scorers(tournament_id, limit=1)
            top_scorer_name = top_scorer[0]["name"] if top_scorer else "N/A"
            top_scorer_goals = top_scorer[0]["goals"] if top_scorer else 0
            
            # Get top assistant
            top_assistant = self.get_top_assistants(tournament_id, limit=1)
            top_assistant_name = top_assistant[0]["name"] if top_assistant else "N/A"
            top_assistant_assists = top_assistant[0]["assists"] if top_assistant else 0
            
            return {
                "tournament_id": tournament_id,
                "tournament_name": tournament.name,
                "season": tournament.season,
                "total_matches": total_matches,
                "total_teams": total_teams,
                "total_goals": total_goals,
                "avg_goals_per_match": (
                    round(total_goals / total_matches, 2)
                    if total_matches > 0 else 0
                ),
                "top_scorer": {
                    "name": top_scorer_name,
                    "goals": top_scorer_goals,
                },
                "top_assistant": {
                    "name": top_assistant_name,
                    "assists": top_assistant_assists,
                },
            }
        
        except TournamentNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to calculate tournament summary",
                extra={"tournament_id": tournament_id, "error": str(e)}
            )
            raise DatabaseError("get_tournament_summary", str(e))

    def compare_teams(
        self,
        team1_id: int,
        team2_id: int,
        tournament_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Compara dois times head-to-head.

        Args:
            team1_id: ID do primeiro time.
            team2_id: ID do segundo time.
            tournament_id: Opcional, filtrar por torneio.

        Returns:
            Dicionário com histórico de confrontos diretos.

        Raises:
            TeamNotFound: Se um ou ambos os times não existirem.
        """
        try:
            team1 = self.db.query(Team).filter_by(id=team1_id).first()
            team2 = self.db.query(Team).filter_by(id=team2_id).first()

            if not team1:
                raise TeamNotFound(team1_id)
            if not team2:
                raise TeamNotFound(team2_id)

            query = self.db.query(Match).filter(
                or_(
                    (Match.home_team_id == team1_id) & (Match.away_team_id == team2_id),
                    (Match.home_team_id == team2_id) & (Match.away_team_id == team1_id),
                ),
                Match.status == "finished",
            )

            if tournament_id:
                query = query.filter(Match.tournament_id == tournament_id)

            h2h_matches = query.order_by(Match.match_date.desc()).all()

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
                ],
            }

        except TeamNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to compare teams",
                extra={"team1_id": team1_id, "team2_id": team2_id, "error": str(e)}
            )
            raise DatabaseError("compare_teams", str(e))

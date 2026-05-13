"""
Service layer for team business logic.

Handles team CRUD operations, analytics, and player management.
All database operations are abstracted in this layer.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models import Team, Match, Player, MatchStatistic
from app.schemas import Team as TeamSchema, TeamWithPlayers as TeamWithPlayersSchema
from app.exceptions import TeamNotFound, DatabaseError
from app.services import BaseService
from app.config import logger


class TeamService(BaseService):
    """Service for team business logic.
    
    Handles team CRUD operations, statistics calculations, and analytics.
    """
    
    def get_by_id(self, team_id: int) -> TeamSchema:
        """Fetch team by ID or raise TeamNotFound.
        
        Args:
            team_id: ID of the team to fetch.
        
        Returns:
            TeamSchema with basic team information.
        
        Raises:
            TeamNotFound: If team_id doesn't exist in database.
        """
        try:
            team = self.db.query(Team).filter_by(id=team_id).first()
            
            if not team:
                logger.warning(
                    f"Team not found",
                    extra={"team_id": team_id}
                )
                raise TeamNotFound(team_id)
            
            return TeamSchema.from_orm(team)
        
        except TeamNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to fetch team",
                extra={"team_id": team_id, "error": str(e)}
            )
            raise DatabaseError("get_team", str(e))
    
    def get_with_players(self, team_id: int) -> TeamWithPlayersSchema:
        """Fetch team with all associated players.
        
        Args:
            team_id: ID of the team to fetch.
        
        Returns:
            TeamWithPlayersSchema with team and player list.
        
        Raises:
            TeamNotFound: If team doesn't exist.
        """
        try:
            team = self.db.query(Team).options(
                joinedload(Team.players)
            ).filter_by(id=team_id).first()
            
            if not team:
                raise TeamNotFound(team_id)
            
            return TeamWithPlayersSchema.from_orm(team)
        
        except TeamNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to fetch team with players",
                extra={"team_id": team_id, "error": str(e)}
            )
            raise DatabaseError("get_team_with_players", str(e))
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TeamSchema]:
        """Fetch all teams with pagination.
        
        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
        
        Returns:
            List of TeamSchema objects.
        """
        try:
            teams = self.db.query(Team).offset(skip).limit(limit).all()
            return [TeamSchema.from_orm(t) for t in teams]
        except Exception as e:
            logger.error(
                f"Failed to fetch teams",
                extra={"skip": skip, "limit": limit, "error": str(e)}
            )
            raise DatabaseError("get_teams", str(e))
    
    def get_recent_matches(
        self,
        team_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Fetch recent matches for a team.
        
        Retrieves finished matches for the team, ordered by match date descending.
        Includes opponent, score, and result.
        
        Args:
            team_id: ID of the team.
            limit: Maximum number of recent matches (default: 10).
        
        Returns:
            List of recent match data with scores and results.
        
        Raises:
            TeamNotFound: If team doesn't exist.
        """
        try:
            # Verify team exists
            team = self.db.query(Team).filter_by(id=team_id).first()
            if not team:
                raise TeamNotFound(team_id)
            
            # Fetch recent matches
            matches = self.db.query(Match).filter(
                (Match.home_team_id == team_id) | (Match.away_team_id == team_id),
                Match.status == "finished",
            ).order_by(Match.match_date.desc()).limit(limit).all()
            
            recent_matches = []
            for match in matches:
                is_home = match.home_team_id == team_id
                opponent_id = match.away_team_id if is_home else match.home_team_id
                opponent_name = match.away_team.name if is_home else match.home_team.name
                
                team_score = match.home_score if is_home else match.away_score
                opponent_score = match.away_score if is_home else match.home_score
                
                # Determine result
                if team_score > opponent_score:
                    result = "W"
                elif team_score == opponent_score:
                    result = "D"
                else:
                    result = "L"
                
                recent_matches.append({
                    "match_id": match.id,
                    "date": match.match_date,
                    "opponent_id": opponent_id,
                    "opponent_name": opponent_name,
                    "home": is_home,
                    "score": f"{team_score}-{opponent_score}",
                    "result": result,
                    "tournament_id": match.tournament_id,
                })
            
            return recent_matches
        
        except TeamNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to fetch recent matches",
                extra={"team_id": team_id, "error": str(e)}
            )
            raise DatabaseError("get_recent_matches", str(e))
    
    def get_analytics(self, team_id: int) -> Dict[str, Any]:
        """Calculate team analytics from recent matches.
        
        Computes:
        - Recent form (last 10 matches: W/D/L)
        - Win rate, draw rate, loss rate
        - Goals for/against per match
        - Average possession
        
        Args:
            team_id: ID of the team.
        
        Returns:
            Dictionary with analytics metrics.
        
        Raises:
            TeamNotFound: If team doesn't exist.
        """
        try:
            # Verify team exists
            team = self.db.query(Team).filter_by(id=team_id).first()
            if not team:
                raise TeamNotFound(team_id)
            
            # Fetch recent matches
            recent_matches = self.db.query(Match).filter(
                (Match.home_team_id == team_id) | (Match.away_team_id == team_id),
                Match.status == "finished",
            ).order_by(Match.match_date.desc()).limit(10).all()
            
            # Initialize counters
            total_matches = len(recent_matches)
            wins = 0
            draws = 0
            losses = 0
            goals_for = 0
            goals_against = 0
            possession_values = []
            recent_form = []
            
            # Calculate statistics
            for match in recent_matches:
                is_home = match.home_team_id == team_id
                team_score = match.home_score if is_home else match.away_score
                opponent_score = match.away_score if is_home else match.home_score
                
                goals_for += team_score or 0
                goals_against += opponent_score or 0
                
                if team_score > opponent_score:
                    wins += 1
                    recent_form.insert(0, "W")
                elif team_score == opponent_score:
                    draws += 1
                    recent_form.insert(0, "D")
                else:
                    losses += 1
                    recent_form.insert(0, "L")
                
                # Get possession stats
                stat = self.db.query(MatchStatistic).filter_by(
                    match_id=match.id,
                    team_id=team_id,
                ).first()
                
                if stat and stat.possession:
                    possession_values.append(stat.possession)
            
            # Calculate averages
            avg_possession = (
                sum(possession_values) / len(possession_values)
                if possession_values else 0
            )
            
            return {
                "team_id": team_id,
                "total_matches_recent": total_matches,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "recent_form": "".join(recent_form),
                "win_rate": (wins / total_matches * 100) if total_matches > 0 else 0,
                "draw_rate": (draws / total_matches * 100) if total_matches > 0 else 0,
                "loss_rate": (losses / total_matches * 100) if total_matches > 0 else 0,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "goal_difference": goals_for - goals_against,
                "avg_goals_per_match": (
                    goals_for / total_matches if total_matches > 0 else 0
                ),
                "avg_possession": round(avg_possession, 2),
            }
        
        except TeamNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to calculate team analytics",
                extra={"team_id": team_id, "error": str(e)}
            )
            raise DatabaseError("get_team_analytics", str(e))

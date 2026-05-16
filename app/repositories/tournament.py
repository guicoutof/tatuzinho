"""
Repository for tournament data access operations.

Handles all database queries related to tournaments, including CRUD operations,
standings calculation, and tournament-specific queries. Abstracts data access
logic from business logic layer.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models import Tournament, Match, Team
from app.repositories import BaseRepository
from app.config import logger
from app.exceptions import DatabaseError


class TournamentRepository(BaseRepository[Tournament]):
    """Repository for Tournament model.
    
    Implements CRUD operations and tournament-specific queries with proper
    error handling and query optimization (eager loading, indexes).
    """
    
    def __init__(self, db: Session):
        """Initialize tournament repository.
        
        Args:
            db: SQLAlchemy database session.
        """
        super().__init__(db, "Tournament")
    
    def find_by_id(self, tournament_id: int) -> Optional[Tournament]:
        """Find tournament by primary key with eager-loaded relationships.
        
        Args:
            tournament_id: Tournament ID.
        
        Returns:
            Tournament if found, None otherwise.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            tournament = self.db.query(Tournament).options(
                joinedload(Tournament.teams),
                joinedload(Tournament.matches),
            ).filter(Tournament.id == tournament_id).first()
            
            if tournament:
                logger.debug(f"Found tournament {tournament_id}")
            else:
                logger.debug(f"Tournament {tournament_id} not found")
            
            return tournament
        except Exception as e:
            self._handle_db_error("find_by_id", e)
    
    def find_all(self, skip: int = 0, limit: int = 100) -> List[Tournament]:
        """Find all tournaments with pagination.
        
        Args:
            skip: Number of records to skip (default: 0).
            limit: Maximum records (default: 100).
        
        Returns:
            List of tournaments ordered by creation date.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            tournaments = self.db.query(Tournament).order_by(
                Tournament.created_at.desc()
            ).offset(skip).limit(limit).all()
            
            logger.debug(f"Found {len(tournaments)} tournaments (skip={skip}, limit={limit})")
            return tournaments
        except Exception as e:
            self._handle_db_error("find_all", e)
    
    def find_by_source_id(self, source_id: str, source: str = "sofascore") -> Optional[Tournament]:
        """Find tournament by source ID and source.
        
        Args:
            source_id: External source ID.
            source: Data source ("sofascore" or "statsbomb").
        
        Returns:
            Tournament if found, None otherwise.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            tournament = self.db.query(Tournament).filter(
                Tournament.source_id == source_id,
                Tournament.source == source,
            ).first()
            
            if tournament:
                logger.debug(f"Found tournament with source_id {source_id} from {source}")
            
            return tournament
        except Exception as e:
            self._handle_db_error("find_by_source_id", e)
    
    def find_by_name(self, name: str) -> Optional[Tournament]:
        """Find tournament by name (case-insensitive).
        
        Args:
            name: Tournament name.
        
        Returns:
            Tournament if found, None otherwise.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            tournament = self.db.query(Tournament).filter(
                Tournament.name.ilike(name)
            ).first()
            
            return tournament
        except Exception as e:
            self._handle_db_error("find_by_name", e)
    
    def create(self, obj_in: Dict[str, Any]) -> Tournament:
        """Create new tournament.
        
        Args:
            obj_in: Dictionary with tournament data.
        
        Returns:
            Newly created tournament.
        
        Raises:
            DatabaseError: If creation fails.
        """
        try:
            tournament = Tournament(**obj_in)
            self.db.add(tournament)
            self.commit()
            self.refresh(tournament)
            
            logger.info(
                f"Created tournament {tournament.id}",
                extra={"tournament_id": tournament.id, "name": tournament.name},
            )
            return tournament
        except Exception as e:
            self._handle_db_error("create", e)
    
    def update(self, tournament_id: int, obj_in: Dict[str, Any]) -> Optional[Tournament]:
        """Update existing tournament.
        
        Args:
            tournament_id: Tournament ID to update.
            obj_in: Dictionary with updated data.
        
        Returns:
            Updated tournament if found, None otherwise.
        
        Raises:
            DatabaseError: If update fails.
        """
        try:
            tournament = self.find_by_id(tournament_id)
            if not tournament:
                logger.debug(f"Tournament {tournament_id} not found for update")
                return None
            
            for key, value in obj_in.items():
                if hasattr(tournament, key):
                    setattr(tournament, key, value)
            
            self.commit()
            self.refresh(tournament)
            
            logger.info(
                f"Updated tournament {tournament_id}",
                extra={"tournament_id": tournament_id},
            )
            return tournament
        except Exception as e:
            self._handle_db_error("update", e)
    
    def delete(self, tournament_id: int) -> bool:
        """Delete tournament (cascade deletes matches, teams in tournament context).
        
        Args:
            tournament_id: Tournament ID to delete.
        
        Returns:
            True if deleted, False if not found.
        
        Raises:
            DatabaseError: If deletion fails.
        """
        try:
            tournament = self.find_by_id(tournament_id)
            if not tournament:
                logger.debug(f"Tournament {tournament_id} not found for deletion")
                return False
            
            self.db.delete(tournament)
            self.commit()
            
            logger.info(
                f"Deleted tournament {tournament_id}",
                extra={"tournament_id": tournament_id},
            )
            return True
        except Exception as e:
            self._handle_db_error("delete", e)
    
    def get_standings(self, tournament_id: int) -> List[Dict[str, Any]]:
        """Calculate tournament standings from finished matches.
        
        Aggregates match results by team and calculates points, goal differential.
        Results should be ordered by points (descending), then goal differential.
        
        Args:
            tournament_id: Tournament ID.
        
        Returns:
            List of team standings with points, wins, losses, goals.
        
        Raises:
            DatabaseError: If calculation fails.
        """
        try:
            # Get all teams in tournament
            teams = self.db.query(Team).join(
                Match, or_(
                    Match.home_team_id == Team.id,
                    Match.away_team_id == Team.id,
                )
            ).filter(Match.tournament_id == tournament_id).distinct().all()
            
            standings = []
            
            for team in teams:
                home_matches = self.db.query(Match).filter(
                    and_(
                        Match.tournament_id == tournament_id,
                        Match.home_team_id == team.id,
                        Match.status == "finished",
                    )
                ).all()
                
                away_matches = self.db.query(Match).filter(
                    and_(
                        Match.tournament_id == tournament_id,
                        Match.away_team_id == team.id,
                        Match.status == "finished",
                    )
                ).all()
                
                wins = 0
                draws = 0
                losses = 0
                goals_for = 0
                goals_against = 0
                
                # Home matches
                for match in home_matches:
                    goals_for += match.home_score or 0
                    goals_against += match.away_score or 0
                    
                    if match.home_score > match.away_score:
                        wins += 1
                    elif match.home_score == match.away_score:
                        draws += 1
                    else:
                        losses += 1
                
                # Away matches
                for match in away_matches:
                    goals_for += match.away_score or 0
                    goals_against += match.home_score or 0
                    
                    if match.away_score > match.home_score:
                        wins += 1
                    elif match.away_score == match.home_score:
                        draws += 1
                    else:
                        losses += 1
                
                points = wins * 3 + draws
                goal_difference = goals_for - goals_against
                
                standings.append({
                    "team_id": team.id,
                    "team_name": team.name,
                    "team_code": team.code,
                    "played": len(home_matches) + len(away_matches),
                    "wins": wins,
                    "draws": draws,
                    "losses": losses,
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                    "goal_difference": goal_difference,
                    "points": points,
                })
            
            # Sort by points DESC, then goal difference DESC
            standings.sort(key=lambda x: (-x["points"], -x["goal_difference"]))
            
            logger.debug(
                f"Calculated standings for tournament {tournament_id}",
                extra={"tournament_id": tournament_id, "teams": len(standings)},
            )
            return standings
        except Exception as e:
            self._handle_db_error("get_standings", e)
    
    def get_matches(
        self,
        tournament_id: int,
        status: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> List[Match]:
        """Get matches for tournament with optional filters.
        
        Args:
            tournament_id: Tournament ID.
            status: Filter by match status (scheduled, inprogress, finished, cancelled).
            phase: Filter by match phase (group, round_of_16, quarter, semi, final).
        
        Returns:
            List of matches matching criteria.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            query = self.db.query(Match).filter(
                Match.tournament_id == tournament_id
            )
            
            if status:
                query = query.filter(Match.status == status)
            
            if phase:
                query = query.filter(Match.phase == phase)
            
            matches = query.order_by(Match.match_date.desc()).all()
            
            logger.debug(
                f"Found {len(matches)} matches for tournament {tournament_id}",
                extra={"tournament_id": tournament_id, "count": len(matches)},
            )
            return matches
        except Exception as e:
            self._handle_db_error("get_matches", e)

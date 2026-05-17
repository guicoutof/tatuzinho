"""
Repository for team data access operations.

Handles all database queries related to teams, including CRUD operations,
team roster retrieval, and team-specific queries. Abstracts data access
logic from business logic layer.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload

from app.models import Team, Player, Match
from app.repositories import BaseRepository
from app.config import logger
from app.exceptions import DatabaseError


class TeamRepository(BaseRepository[Team]):
    """Repository for Team model.
    
    Implements CRUD operations and team-specific queries with proper
    error handling and query optimization (eager loading, relationships).
    """
    
    def __init__(self, db: Session):
        """Initialize team repository.
        
        Args:
            db: SQLAlchemy database session.
        """
        super().__init__(db, "Team")
    
    def find_by_id(self, team_id: int) -> Optional[Team]:
        """Find team by primary key.
        
        Args:
            team_id: Team ID.
        
        Returns:
            Team if found, None otherwise.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            team = self.db.query(Team).filter(Team.id == team_id).first()
            
            if team:
                logger.debug(f"Found team {team_id}")
            else:
                logger.debug(f"Team {team_id} not found")
            
            return team
        except Exception as e:
            self._handle_db_error("find_by_id", e)
    
    def find_by_id_with_players(self, team_id: int) -> Optional[Team]:
        """Find team by ID with eager-loaded players.
        
        Args:
            team_id: Team ID.
        
        Returns:
            Team with players if found, None otherwise.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            team = self.db.query(Team).options(
                joinedload(Team.players),
            ).filter(Team.id == team_id).first()
            
            if team:
                logger.debug(f"Found team {team_id} with {len(team.players)} players")
            
            return team
        except Exception as e:
            self._handle_db_error("find_by_id_with_players", e)
    
    def find_all(self, skip: int = 0, limit: int = 100) -> List[Team]:
        """Find all teams with pagination.
        
        Args:
            skip: Number of records to skip (default: 0).
            limit: Maximum records (default: 100).
        
        Returns:
            List of teams ordered by name.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            teams = self.db.query(Team).order_by(
                Team.name.asc()
            ).offset(skip).limit(limit).all()
            
            logger.debug(f"Found {len(teams)} teams (skip={skip}, limit={limit})")
            return teams
        except Exception as e:
            self._handle_db_error("find_all", e)
    
    def find_by_source_id(self, source_id: int, source: str = "statsbomb") -> Optional[Team]:
        """Find team by source ID and source.
        
        Args:
            source_id: External source ID.
            source: Data source ("statsbomb").
        
        Returns:
            Team if found, None otherwise.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            team = self.db.query(Team).filter(
                Team.source_id == source_id,
                Team.source == source,
            ).first()
            
            return team
        except Exception as e:
            self._handle_db_error("find_by_source_id", e)
    
    def find_by_code(self, code: str) -> Optional[Team]:
        """Find team by country code (ISO3, case-insensitive).

        Args:
            code: ISO3 country code (e.g., 'BRA', 'FRA').

        Returns:
            Team if found, None otherwise.

        Raises:
            DatabaseError: If query fails.
        """
        try:
            team = self.db.query(Team).filter(
                Team.code.ilike(code)
            ).first()

            return team
        except Exception as e:
            self._handle_db_error("find_by_code", e)

    def find_by_name(self, name: str) -> Optional[Team]:
        """Find team by name (case-insensitive).

        Args:
            name: Team name (e.g., 'Brazil', 'brazil').

        Returns:
            Team if found, None otherwise.

        Raises:
            DatabaseError: If query fails.
        """
        try:
            team = self.db.query(Team).filter(
                Team.name.ilike(name)
            ).first()

            return team
        except Exception as e:
            self._handle_db_error("find_by_name", e)
    
    def create(self, obj_in: Dict[str, Any]) -> Team:
        """Create new team.
        
        Args:
            obj_in: Dictionary with team data.
        
        Returns:
            Newly created team.
        
        Raises:
            DatabaseError: If creation fails.
        """
        try:
            team = Team(**obj_in)
            self.db.add(team)
            self.commit()
            self.refresh(team)
            
            logger.info(
                f"Created team {team.id}",
                extra={"team_id": team.id, "name": team.name},
            )
            return team
        except Exception as e:
            self._handle_db_error("create", e)
    
    def update(self, team_id: int, obj_in: Dict[str, Any]) -> Optional[Team]:
        """Update existing team.
        
        Args:
            team_id: Team ID to update.
            obj_in: Dictionary with updated data.
        
        Returns:
            Updated team if found, None otherwise.
        
        Raises:
            DatabaseError: If update fails.
        """
        try:
            team = self.find_by_id(team_id)
            if not team:
                logger.debug(f"Team {team_id} not found for update")
                return None
            
            for key, value in obj_in.items():
                if hasattr(team, key):
                    setattr(team, key, value)
            
            self.commit()
            self.refresh(team)
            
            logger.info(f"Updated team {team_id}", extra={"team_id": team_id})
            return team
        except Exception as e:
            self._handle_db_error("update", e)
    
    def delete(self, team_id: int) -> bool:
        """Delete team (cascade deletes players, match associations).
        
        Args:
            team_id: Team ID to delete.
        
        Returns:
            True if deleted, False if not found.
        
        Raises:
            DatabaseError: If deletion fails.
        """
        try:
            team = self.find_by_id(team_id)
            if not team:
                logger.debug(f"Team {team_id} not found for deletion")
                return False
            
            self.db.delete(team)
            self.commit()
            
            logger.info(f"Deleted team {team_id}", extra={"team_id": team_id})
            return True
        except Exception as e:
            self._handle_db_error("delete", e)
    
    def get_players(self, team_id: int) -> List[Player]:
        """Get all players for a team.
        
        Args:
            team_id: Team ID.
        
        Returns:
            List of players for the team.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            players = self.db.query(Player).filter(
                Player.team_id == team_id
            ).order_by(Player.number.asc()).all()
            
            logger.debug(
                f"Found {len(players)} players for team {team_id}",
                extra={"team_id": team_id, "count": len(players)},
            )
            return players
        except Exception as e:
            self._handle_db_error("get_players", e)
    
    def get_recent_matches(
        self,
        team_id: int,
        status: str = "finished",
        limit: int = 10,
    ) -> List[Match]:
        """Get recent matches for a team.
        
        Args:
            team_id: Team ID.
            status: Match status filter (default: "finished").
            limit: Maximum matches (default: 10).
        
        Returns:
            List of recent matches.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            from sqlalchemy import or_
            
            matches = self.db.query(Match).filter(
                or_(
                    Match.home_team_id == team_id,
                    Match.away_team_id == team_id,
                ),
                Match.status == status,
            ).order_by(Match.match_date.desc()).limit(limit).all()
            
            logger.debug(
                f"Found {len(matches)} recent matches for team {team_id}",
                extra={"team_id": team_id, "count": len(matches)},
            )
            return matches
        except Exception as e:
            self._handle_db_error("get_recent_matches", e)

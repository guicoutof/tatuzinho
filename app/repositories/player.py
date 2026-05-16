"""
Repository for player data access operations.

Handles all database queries related to players, including CRUD operations
and player-specific queries. Abstracts data access logic from business logic layer.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload

from app.models import Player
from app.repositories import BaseRepository
from app.config import logger
from app.exceptions import DatabaseError


class PlayerRepository(BaseRepository[Player]):
    """Repository for Player model.
    
    Implements CRUD operations and player-specific queries with proper
    error handling and query optimization (eager loading, filtering).
    """
    
    def __init__(self, db: Session):
        """Initialize player repository.
        
        Args:
            db: SQLAlchemy database session.
        """
        super().__init__(db, "Player")
    
    def find_by_id(self, player_id: int) -> Optional[Player]:
        """Find player by primary key with eager-loaded relationships.
        
        Args:
            player_id: Player ID.
        
        Returns:
            Player if found, None otherwise.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            player = self.db.query(Player).options(
                joinedload(Player.team),
            ).filter(Player.id == player_id).first()
            
            if player:
                logger.debug(f"Found player {player_id}")
            else:
                logger.debug(f"Player {player_id} not found")
            
            return player
        except Exception as e:
            self._handle_db_error("find_by_id", e)
    
    def find_all(self, skip: int = 0, limit: int = 100) -> List[Player]:
        """Find all players with pagination.
        
        Args:
            skip: Number of records to skip (default: 0).
            limit: Maximum records (default: 100).
        
        Returns:
            List of players ordered by name.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            players = self.db.query(Player).order_by(
                Player.name.asc()
            ).offset(skip).limit(limit).all()
            
            logger.debug(f"Found {len(players)} players (skip={skip}, limit={limit})")
            return players
        except Exception as e:
            self._handle_db_error("find_all", e)
    
    def find_by_source_id(self, source_id: int, source: str = "sofascore") -> Optional[Player]:
        """Find player by source ID and source.
        
        Args:
            source_id: External source ID.
            source: Data source ("sofascore" or "statsbomb").
        
        Returns:
            Player if found, None otherwise.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            player = self.db.query(Player).filter(
                Player.source_id == source_id,
                Player.source == source,
            ).first()
            
            return player
        except Exception as e:
            self._handle_db_error("find_by_source_id", e)
    
    def find_by_team(self, team_id: int, skip: int = 0, limit: int = 100) -> List[Player]:
        """Find players by team with pagination.
        
        Args:
            team_id: Team ID.
            skip: Number of records to skip (default: 0).
            limit: Maximum records (default: 100).
        
        Returns:
            List of players for team, ordered by number.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            players = self.db.query(Player).filter(
                Player.team_id == team_id
            ).order_by(Player.number.asc()).offset(skip).limit(limit).all()
            
            logger.debug(
                f"Found {len(players)} players for team {team_id}",
                extra={"team_id": team_id},
            )
            return players
        except Exception as e:
            self._handle_db_error("find_by_team", e)
    
    def create(self, obj_in: Dict[str, Any]) -> Player:
        """Create new player.
        
        Args:
            obj_in: Dictionary with player data.
        
        Returns:
            Newly created player.
        
        Raises:
            DatabaseError: If creation fails.
        """
        try:
            player = Player(**obj_in)
            self.db.add(player)
            self.commit()
            self.refresh(player)
            
            logger.info(
                f"Created player {player.id}",
                extra={"player_id": player.id, "name": player.name},
            )
            return player
        except Exception as e:
            self._handle_db_error("create", e)
    
    def update(self, player_id: int, obj_in: Dict[str, Any]) -> Optional[Player]:
        """Update existing player.
        
        Args:
            player_id: Player ID to update.
            obj_in: Dictionary with updated data.
        
        Returns:
            Updated player if found, None otherwise.
        
        Raises:
            DatabaseError: If update fails.
        """
        try:
            player = self.find_by_id(player_id)
            if not player:
                logger.debug(f"Player {player_id} not found for update")
                return None
            
            for key, value in obj_in.items():
                if hasattr(player, key):
                    setattr(player, key, value)
            
            self.commit()
            self.refresh(player)
            
            logger.info(f"Updated player {player_id}", extra={"player_id": player_id})
            return player
        except Exception as e:
            self._handle_db_error("update", e)
    
    def delete(self, player_id: int) -> bool:
        """Delete player.
        
        Args:
            player_id: Player ID to delete.
        
        Returns:
            True if deleted, False if not found.
        
        Raises:
            DatabaseError: If deletion fails.
        """
        try:
            player = self.find_by_id(player_id)
            if not player:
                logger.debug(f"Player {player_id} not found for deletion")
                return False
            
            self.db.delete(player)
            self.commit()
            
            logger.info(f"Deleted player {player_id}", extra={"player_id": player_id})
            return True
        except Exception as e:
            self._handle_db_error("delete", e)
    
    def find_by_position(self, position: str) -> List[Player]:
        """Find all players by position.
        
        Args:
            position: Position (e.g., 'GK', 'DEF', 'MID', 'FWD').
        
        Returns:
            List of players with that position.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            players = self.db.query(Player).filter(
                Player.position == position
            ).order_by(Player.name.asc()).all()
            
            logger.debug(
                f"Found {len(players)} players at position {position}",
                extra={"position": position},
            )
            return players
        except Exception as e:
            self._handle_db_error("find_by_position", e)
    
    def find_top_scorers_by_team(self, team_id: int, limit: int = 5) -> List[Player]:
        """Find top scorers for a team.
        
        Args:
            team_id: Team ID.
            limit: Maximum players to return (default: 5).
        
        Returns:
            List of top scorers ordered by goals descending.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            players = self.db.query(Player).filter(
                Player.team_id == team_id
            ).order_by(Player.goals.desc()).limit(limit).all()
            
            logger.debug(
                f"Found {len(players)} top scorers for team {team_id}",
                extra={"team_id": team_id, "limit": limit},
            )
            return players
        except Exception as e:
            self._handle_db_error("find_top_scorers_by_team", e)

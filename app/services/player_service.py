"""
Service layer for player business logic.

Handles player CRUD operations and statistics management.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload

from app.models import Player, Team
from app.schemas import Player as PlayerSchema
from app.exceptions import PlayerNotFound, DatabaseError
from app.services import BaseService
from app.config import logger


class PlayerService(BaseService):
    """Service for player business logic.
    
    Handles player CRUD operations and statistics management.
    """
    
    def get_by_id(self, player_id: int) -> PlayerSchema:
        """Fetch player by ID or raise PlayerNotFound.
        
        Args:
            player_id: ID of the player to fetch.
        
        Returns:
            PlayerSchema with player information.
        
        Raises:
            PlayerNotFound: If player_id doesn't exist.
        """
        try:
            player = self.db.query(Player).options(
                joinedload(Player.team)
            ).filter_by(id=player_id).first()
            
            if not player:
                logger.warning(
                    f"Player not found",
                    extra={"player_id": player_id}
                )
                raise PlayerNotFound(player_id)
            
            return PlayerSchema.from_orm(player)
        
        except PlayerNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to fetch player",
                extra={"player_id": player_id, "error": str(e)}
            )
            raise DatabaseError("get_player", str(e))
    
    def get_by_team(
        self,
        team_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PlayerSchema]:
        """Fetch all players in a team.
        
        Args:
            team_id: ID of the team.
            skip: Number of records to skip for pagination.
            limit: Maximum number of records to return.
        
        Returns:
            List of PlayerSchema objects.
        """
        try:
            players = self.db.query(Player).filter_by(
                team_id=team_id
            ).offset(skip).limit(limit).all()
            
            return [PlayerSchema.from_orm(p) for p in players]
        except Exception as e:
            logger.error(
                f"Failed to fetch team players",
                extra={"team_id": team_id, "error": str(e)}
            )
            raise DatabaseError("get_team_players", str(e))
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PlayerSchema]:
        """Fetch all players with pagination.
        
        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
        
        Returns:
            List of PlayerSchema objects.
        """
        try:
            players = self.db.query(Player).offset(skip).limit(limit).all()
            return [PlayerSchema.from_orm(p) for p in players]
        except Exception as e:
            logger.error(
                f"Failed to fetch players",
                extra={"skip": skip, "limit": limit, "error": str(e)}
            )
            raise DatabaseError("get_players", str(e))

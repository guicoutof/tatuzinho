"""
Service layer for tournament business logic.

Handles tournament-related operations like creation, retrieval, and updates.
All database operations are delegated to TournamentRepository (data access layer).
This layer enforces business rules and orchestrates complex operations.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.schemas import TournamentCreate, Tournament as TournamentSchema
from app.exceptions import (
    TournamentNotFound,
    DuplicateEntityError,
    DatabaseError,
)
from app.services import BaseService
from app.repositories.tournament import TournamentRepository
from app.config import logger


class TournamentService(BaseService):
    """Service for tournament business logic.
    
    Handles tournament CRUD operations, standings calculations, and related
    queries. All database operations are delegated to TournamentRepository.
    """
    
    def __init__(self, db: Session):
        """Initialize tournament service with repository.
        
        Args:
            db: Database session.
        """
        super().__init__(db)
        self.repository = TournamentRepository(db)
    
    def create(self, tournament_in: TournamentCreate) -> TournamentSchema:
        """Create a new tournament in the database.
        
        Validates that tournament with same sofascore_id doesn't exist.
        Raises DuplicateEntityError if tournament already exists.
        
        Args:
            tournament_in: Tournament creation schema with validation.
        
        Returns:
            TournamentSchema: Newly created tournament with all fields.
        
        Raises:
            DuplicateEntityError: If tournament with same sofascore_id exists.
            DatabaseError: If database operation fails.
        """
        try:
            # Check if tournament already exists
            existing = self.repository.find_by_sofascore_id(
                tournament_in.sofascore_id
            )
            
            if existing:
                logger.warning(
                    f"Attempted to create duplicate tournament",
                    extra={
                        "sofascore_id": tournament_in.sofascore_id,
                        "name": tournament_in.name,
                    }
                )
                raise DuplicateEntityError(
                    entity_type="Tournament",
                    identifier="sofascore_id",
                    value=str(tournament_in.sofascore_id),
                )
            
            # Create new tournament
            tournament = self.repository.create(tournament_in.model_dump())
            
            logger.info(
                f"Tournament created successfully",
                extra={
                    "tournament_id": tournament.id,
                    "name": tournament.name,
                    "sofascore_id": tournament.sofascore_id,
                }
            )
            
            return TournamentSchema.from_orm(tournament)
        
        except DuplicateEntityError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to create tournament",
                extra={
                    "error": str(e),
                    "sofascore_id": tournament_in.sofascore_id,
                }
            )
            raise
    
    def get_by_id(self, tournament_id: int) -> TournamentSchema:
        """Fetch tournament by ID or raise TournamentNotFound.
        
        Uses eager loading to prevent N+1 queries when accessing relationships.
        
        Args:
            tournament_id: ID of the tournament to fetch.
        
        Returns:
            TournamentSchema: Tournament with all fields.
        
        Raises:
            TournamentNotFound: If tournament_id doesn't exist in database.
        """
        try:
            tournament = self.repository.find_by_id(tournament_id)
            
            if not tournament:
                logger.warning(
                    f"Tournament not found",
                    extra={"tournament_id": tournament_id}
                )
                raise TournamentNotFound(tournament_id)
            
            return TournamentSchema.from_orm(tournament)
        
        except TournamentNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to fetch tournament",
                extra={
                    "tournament_id": tournament_id,
                    "error": str(e),
                }
            )
            raise
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TournamentSchema]:
        """Fetch all tournaments with pagination.
        
        Args:
            skip: Number of records to skip (for pagination).
            limit: Maximum number of records to return.
        
        Returns:
            List of TournamentSchema objects.
        """
        try:
            tournaments = self.repository.find_all(skip=skip, limit=limit)
            
            return [
                TournamentSchema.from_orm(t) for t in tournaments
            ]
        except Exception as e:
            logger.error(
                f"Failed to fetch tournaments",
                extra={
                    "skip": skip,
                    "limit": limit,
                    "error": str(e),
                }
            )
            raise
    
    def get_by_sofascore_id(self, sofascore_id: int) -> Optional[TournamentSchema]:
        """Fetch tournament by SofaScore ID.
        
        Args:
            sofascore_id: SofaScore external ID.
        
        Returns:
            TournamentSchema if found, None otherwise.
        """
        try:
            tournament = self.repository.find_by_sofascore_id(sofascore_id)
            
            if tournament:
                return TournamentSchema.from_orm(tournament)
            return None
        except Exception as e:
            logger.error(
                f"Failed to fetch tournament by sofascore_id",
                extra={
                    "sofascore_id": sofascore_id,
                    "error": str(e),
                }
            )
            raise
    
    def update(
        self,
        tournament_id: int,
        tournament_update: dict,
    ) -> TournamentSchema:
        """Update tournament fields.
        
        Args:
            tournament_id: ID of tournament to update.
            tournament_update: Dictionary of fields to update.
        
        Returns:
            Updated TournamentSchema.
        
        Raises:
            TournamentNotFound: If tournament doesn't exist.
        """
        try:
            tournament = self.repository.update(tournament_id, tournament_update)
            
            if not tournament:
                raise TournamentNotFound(tournament_id)
            
            logger.info(
                f"Tournament updated",
                extra={
                    "tournament_id": tournament_id,
                    "fields_updated": list(tournament_update.keys()),
                }
            )
            
            return TournamentSchema.from_orm(tournament)
        
        except TournamentNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to update tournament",
                extra={
                    "tournament_id": tournament_id,
                    "error": str(e),
                }
            )
            raise
    
    def delete(self, tournament_id: int) -> bool:
        """Delete tournament and all related data.
        
        Args:
            tournament_id: ID of tournament to delete.
        
        Returns:
            True if deletion was successful.
        
        Raises:
            TournamentNotFound: If tournament doesn't exist.
        """
        try:
            success = self.repository.delete(tournament_id)
            
            if not success:
                raise TournamentNotFound(tournament_id)
            
            logger.info(
                f"Tournament deleted",
                extra={"tournament_id": tournament_id}
            )
            
            return True
        
        except TournamentNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to delete tournament",
                extra={
                    "tournament_id": tournament_id,
                    "error": str(e),
                }
            )
            raise
    
    def get_standings(
        self,
        tournament_id: int,
    ) -> List[dict]:
        """Calculate current tournament standings.
        
        Aggregates match results by team and returns standings sorted by points.
        Results are calculated directly from matches (not cached by this service).
        Implement caching at the router level for performance.
        
        Args:
            tournament_id: ID of the tournament.
        
        Returns:
            List of team standings with points, wins, draws, losses, goals.
        
        Raises:
            TournamentNotFound: If tournament doesn't exist.
        """
        try:
            # Verify tournament exists
            tournament = self.repository.find_by_id(tournament_id)
            if not tournament:
                raise TournamentNotFound(tournament_id)
            
            # Calculate and return standings from repository
            standings = self.repository.get_standings(tournament_id)
            
            logger.debug(
                f"Calculated standings for tournament {tournament_id}",
                extra={"tournament_id": tournament_id, "teams": len(standings)},
            )
            
            return standings
        
        except TournamentNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to calculate standings",
                extra={
                    "tournament_id": tournament_id,
                    "error": str(e),
                }
            )
            raise

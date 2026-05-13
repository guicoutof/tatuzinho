"""
Service layer for tournament business logic.

Handles tournament-related operations like creation, retrieval, and updates.
All database operations are abstracted and business rules are enforced here.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models import Tournament, Match, Team
from app.schemas import TournamentCreate, Tournament as TournamentSchema
from app.exceptions import (
    TournamentNotFound,
    DuplicateEntityError,
    DatabaseError,
)
from app.services import BaseService
from app.config import logger


class TournamentService(BaseService):
    """Service for tournament business logic.
    
    Handles tournament CRUD operations, standings calculations, and related
    queries. All database operations are isolated in this layer.
    """
    
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
            existing = self.db.query(Tournament).filter_by(
                sofascore_id=tournament_in.sofascore_id
            ).first()
            
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
            tournament = Tournament(**tournament_in.model_dump())
            self.db.add(tournament)
            self.commit()
            self.refresh(tournament)
            
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
            self.rollback()
            logger.error(
                f"Failed to create tournament",
                extra={
                    "error": str(e),
                    "sofascore_id": tournament_in.sofascore_id,
                }
            )
            raise DatabaseError("create_tournament", str(e))
    
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
            tournament = self.db.query(Tournament).filter_by(
                id=tournament_id
            ).first()
            
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
            raise DatabaseError("get_tournament", str(e))
    
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
            tournaments = self.db.query(Tournament).offset(
                skip
            ).limit(limit).all()
            
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
            raise DatabaseError("get_tournaments", str(e))
    
    def get_by_sofascore_id(self, sofascore_id: int) -> Optional[TournamentSchema]:
        """Fetch tournament by SofaScore ID.
        
        Args:
            sofascore_id: SofaScore external ID.
        
        Returns:
            TournamentSchema if found, None otherwise.
        """
        try:
            tournament = self.db.query(Tournament).filter_by(
                sofascore_id=sofascore_id
            ).first()
            
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
            raise DatabaseError("get_tournament_by_sofascore_id", str(e))
    
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
            tournament = self.db.query(Tournament).filter_by(
                id=tournament_id
            ).first()
            
            if not tournament:
                raise TournamentNotFound(tournament_id)
            
            for key, value in tournament_update.items():
                if hasattr(tournament, key):
                    setattr(tournament, key, value)
            
            self.commit()
            self.refresh(tournament)
            
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
            self.rollback()
            logger.error(
                f"Failed to update tournament",
                extra={
                    "tournament_id": tournament_id,
                    "error": str(e),
                }
            )
            raise DatabaseError("update_tournament", str(e))
    
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
            tournament = self.db.query(Tournament).filter_by(
                id=tournament_id
            ).first()
            
            if not tournament:
                raise TournamentNotFound(tournament_id)
            
            self.db.delete(tournament)
            self.commit()
            
            logger.info(
                f"Tournament deleted",
                extra={"tournament_id": tournament_id}
            )
            
            return True
        
        except TournamentNotFound:
            raise
        except Exception as e:
            self.rollback()
            logger.error(
                f"Failed to delete tournament",
                extra={
                    "tournament_id": tournament_id,
                    "error": str(e),
                }
            )
            raise DatabaseError("delete_tournament", str(e))
    
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
            tournament = self.db.query(Tournament).filter_by(
                id=tournament_id
            ).first()
            
            if not tournament:
                raise TournamentNotFound(tournament_id)
            
            # Query all teams in tournament
            teams = self.db.query(Team).join(
                Tournament.teams
            ).filter(
                Tournament.id == tournament_id
            ).all()
            
            standings = []
            for team in teams:
                # Calculate statistics
                home_matches = self.db.query(Match).filter_by(
                    tournament_id=tournament_id,
                    home_team_id=team.id,
                    status="finished",
                ).all()
                
                away_matches = self.db.query(Match).filter_by(
                    tournament_id=tournament_id,
                    away_team_id=team.id,
                    status="finished",
                ).all()
                
                all_matches = home_matches + away_matches
                
                wins = sum(
                    1 for m in home_matches if m.home_score > m.away_score
                ) + sum(
                    1 for m in away_matches if m.away_score > m.home_score
                )
                
                draws = sum(
                    1 for m in home_matches if m.home_score == m.away_score
                ) + sum(
                    1 for m in away_matches if m.away_score == m.home_score
                )
                
                losses = len(all_matches) - wins - draws
                
                goals_for = sum(
                    m.home_score for m in home_matches
                ) + sum(
                    m.away_score for m in away_matches
                )
                
                goals_against = sum(
                    m.away_score for m in home_matches
                ) + sum(
                    m.home_score for m in away_matches
                )
                
                points = wins * 3 + draws
                
                standings.append({
                    "team_id": team.id,
                    "team_name": team.name,
                    "team_code": team.code,
                    "matches_played": len(all_matches),
                    "wins": wins,
                    "draws": draws,
                    "losses": losses,
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                    "goal_difference": goals_for - goals_against,
                    "points": points,
                })
            
            # Sort by points (descending), then by goal difference
            standings.sort(
                key=lambda x: (-x["points"], -x["goal_difference"])
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
            raise DatabaseError("get_standings", str(e))

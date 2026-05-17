"""
Repository for match data access operations.

Handles all database queries related to matches, including CRUD operations,
filtering by tournament/phase/group, and statistics retrieval. Abstracts
data access logic from business logic layer.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.models import Match, MatchStatistic
from app.repositories import BaseRepository
from app.config import logger
from app.exceptions import DatabaseError


class MatchRepository(BaseRepository[Match]):
    """Repository for Match model.
    
    Implements CRUD operations and match-specific queries with proper
    error handling and query optimization (eager loading, filtering).
    """
    
    def __init__(self, db: Session):
        """Initialize match repository.
        
        Args:
            db: SQLAlchemy database session.
        """
        super().__init__(db, "Match")
    
    def find_by_id(self, match_id: int) -> Optional[Match]:
        """Find match by primary key with eager-loaded relationships.
        
        Args:
            match_id: Match ID.
        
        Returns:
            Match if found, None otherwise.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            match = self.db.query(Match).options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
                joinedload(Match.tournament),
            ).filter(Match.id == match_id).first()
            
            if match:
                logger.debug(f"Found match {match_id}")
            else:
                logger.debug(f"Match {match_id} not found")
            
            return match
        except Exception as e:
            self._handle_db_error("find_by_id", e)
    
    def find_all(self, skip: int = 0, limit: int = 100) -> List[Match]:
        """Find all matches with pagination.
        
        Args:
            skip: Number of records to skip (default: 0).
            limit: Maximum records (default: 100).
        
        Returns:
            List of matches ordered by date descending.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            matches = self.db.query(Match).order_by(
                Match.match_date.desc()
            ).offset(skip).limit(limit).all()
            
            logger.debug(f"Found {len(matches)} matches (skip={skip}, limit={limit})")
            return matches
        except Exception as e:
            self._handle_db_error("find_all", e)
    
    def find_by_source_id(self, source_id: int, source: str = "statsbomb") -> Optional[Match]:
        """Find match by source ID and source.
        
        Args:
            source_id: External source ID.
            source: Data source ("statsbomb").
        
        Returns:
            Match if found, None otherwise.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            match = self.db.query(Match).filter(
                Match.source_id == source_id,
                Match.source == source,
            ).first()
            
            return match
        except Exception as e:
            self._handle_db_error("find_by_source_id", e)
    
    def create(self, obj_in: Dict[str, Any]) -> Match:
        """Create new match.
        
        Args:
            obj_in: Dictionary with match data.
        
        Returns:
            Newly created match.
        
        Raises:
            DatabaseError: If creation fails.
        """
        try:
            match = Match(**obj_in)
            self.db.add(match)
            self.commit()
            self.refresh(match)
            
            logger.info(
                f"Created match {match.id}",
                extra={"match_id": match.id, "tournament_id": match.tournament_id},
            )
            return match
        except Exception as e:
            self._handle_db_error("create", e)
    
    def update(self, match_id: int, obj_in: Dict[str, Any]) -> Optional[Match]:
        """Update existing match.
        
        Args:
            match_id: Match ID to update.
            obj_in: Dictionary with updated data.
        
        Returns:
            Updated match if found, None otherwise.
        
        Raises:
            DatabaseError: If update fails.
        """
        try:
            match = self.find_by_id(match_id)
            if not match:
                logger.debug(f"Match {match_id} not found for update")
                return None
            
            for key, value in obj_in.items():
                if hasattr(match, key):
                    setattr(match, key, value)
            
            self.commit()
            self.refresh(match)
            
            logger.info(
                f"Updated match {match_id}",
                extra={"match_id": match_id},
            )
            return match
        except Exception as e:
            self._handle_db_error("update", e)
    
    def delete(self, match_id: int) -> bool:
        """Delete match (cascade deletes related statistics).
        
        Args:
            match_id: Match ID to delete.
        
        Returns:
            True if deleted, False if not found.
        
        Raises:
            DatabaseError: If deletion fails.
        """
        try:
            match = self.find_by_id(match_id)
            if not match:
                logger.debug(f"Match {match_id} not found for deletion")
                return False
            
            self.db.delete(match)
            self.commit()
            
            logger.info(f"Deleted match {match_id}", extra={"match_id": match_id})
            return True
        except Exception as e:
            self._handle_db_error("delete", e)
    
    def find_with_filters(
        self,
        tournament_id: Optional[int] = None,
        phase: Optional[str] = None,
        group: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Match]:
        """Find matches with multiple optional filters.
        
        Args:
            tournament_id: Filter by tournament ID.
            phase: Filter by phase (group, round_of_16, quarter, semi, final).
            group: Filter by group letter (A, B, C, etc).
            status: Filter by status (scheduled, inprogress, finished, cancelled).
            skip: Pagination offset (default: 0).
            limit: Maximum records (default: 100).
        
        Returns:
            List of matches matching all filters.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            query = self.db.query(Match)
            
            if tournament_id is not None:
                query = query.filter(Match.tournament_id == tournament_id)
            
            if phase is not None:
                query = query.filter(Match.phase == phase)
            
            if group is not None:
                query = query.filter(Match.group == group)
            
            if status is not None:
                query = query.filter(Match.status == status)
            
            matches = query.order_by(
                Match.match_date.desc()
            ).offset(skip).limit(limit).all()
            
            logger.debug(
                f"Found {len(matches)} matches with filters",
                extra={
                    "tournament_id": tournament_id,
                    "phase": phase,
                    "group": group,
                    "status": status,
                },
            )
            return matches
        except Exception as e:
            self._handle_db_error("find_with_filters", e)
    
    def get_statistics(self, match_id: int) -> List[MatchStatistic]:
        """Get all statistics for a match (by team or player).
        
        Args:
            match_id: Match ID.
        
        Returns:
            List of match statistics records.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            statistics = self.db.query(MatchStatistic).filter(
                MatchStatistic.match_id == match_id
            ).all()
            
            logger.debug(
                f"Found {len(statistics)} statistics for match {match_id}",
                extra={"match_id": match_id},
            )
            return statistics
        except Exception as e:
            self._handle_db_error("get_statistics", e)
    
    def find_team_recent_matches(
        self,
        team_id: int,
        status: str = "finished",
        limit: int = 10,
    ) -> List[Match]:
        """Find recent matches for a team.
        
        Args:
            team_id: Team ID.
            status: Match status filter (default: "finished").
            limit: Maximum matches (default: 10).
        
        Returns:
            List of recent matches for team.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            from sqlalchemy import or_
            
            matches = self.db.query(Match).filter(
                and_(
                    or_(
                        Match.home_team_id == team_id,
                        Match.away_team_id == team_id,
                    ),
                    Match.status == status,
                )
            ).order_by(Match.match_date.desc()).limit(limit).all()
            
            logger.debug(
                f"Found {len(matches)} recent matches for team {team_id}",
                extra={"team_id": team_id, "count": len(matches)},
            )
            return matches
        except Exception as e:
            self._handle_db_error("find_team_recent_matches", e)

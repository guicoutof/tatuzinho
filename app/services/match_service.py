"""
Service layer for match business logic.

Handles match CRUD operations, filtering, statistics, and synchronization.
All database operations are delegated to MatchRepository (data access layer).
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.schemas import Match as MatchSchema
from app.exceptions import MatchNotFound, TournamentNotFound, DatabaseError
from app.services import BaseService
from app.repositories.match import MatchRepository
from app.repositories.tournament import TournamentRepository
from app.config import logger


class MatchService(BaseService):
    """Service for match business logic.
    
    Handles match retrieval with complex filtering, statistics, and sync operations.
    All database operations are delegated to MatchRepository.
    """
    
    def __init__(self, db: Session):
        """Initialize match service with repositories.
        
        Args:
            db: Database session.
        """
        super().__init__(db)
        self.repository = MatchRepository(db)
        self.tournament_repository = TournamentRepository(db)
    
    def get_by_id(self, match_id: int) -> MatchSchema:
        """Fetch match by ID or raise MatchNotFound.
        
        Args:
            match_id: ID of the match to fetch.
        
        Returns:
            MatchSchema with complete match information.
        
        Raises:
            MatchNotFound: If match_id doesn't exist.
        """
        try:
            match = self.repository.find_by_id(match_id)
            
            if not match:
                logger.warning(
                    f"Match not found",
                    extra={"match_id": match_id}
                )
                raise MatchNotFound(match_id)
            
            return MatchSchema.from_orm(match)
        
        except MatchNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to fetch match",
                extra={"match_id": match_id, "error": str(e)}
            )
            raise
    
    def list_with_filters(
        self,
        tournament_id: Optional[int] = None,
        phase: Optional[str] = None,
        group: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[MatchSchema]:
        """List matches with optional filters.
        
        Args:
            tournament_id: Filter by tournament ID.
            phase: Filter by phase (group, round_of_16, quarter, semi, final).
            group: Filter by group (A, B, C, etc).
            status: Filter by status (scheduled, inprogress, finished, cancelled).
            skip: Number of records to skip for pagination.
            limit: Maximum number of records to return.
        
        Returns:
            List of MatchSchema objects sorted by match_date descending.
        """
        try:
            matches = self.repository.find_with_filters(
                tournament_id=tournament_id,
                phase=phase,
                group=group,
                status=status,
                skip=skip,
                limit=limit,
            )
            
            return [MatchSchema.from_orm(m) for m in matches]
        
        except Exception as e:
            logger.error(
                f"Failed to list matches",
                extra={
                    "tournament_id": tournament_id,
                    "filters": {"phase": phase, "group": group, "status": status},
                    "error": str(e),
                }
            )
            raise
    
    def get_statistics(self, match_id: int) -> Dict[str, Any]:
        """Fetch detailed statistics for a match.
        
        Includes possession, shots, passes, tackles, fouls, etc. for both teams.
        
        Args:
            match_id: ID of the match.
        
        Returns:
            Dictionary with home and away team statistics.
        
        Raises:
            MatchNotFound: If match doesn't exist.
        """
        try:
            match = self.db.query(Match).filter_by(id=match_id).first()
            
            if not match:
                raise MatchNotFound(match_id)
            
            # Fetch statistics for both teams
            home_stats = self.db.query(MatchStatistic).filter_by(
                match_id=match_id,
                team_id=match.home_team_id,
            ).first()
            
            away_stats = self.db.query(MatchStatistic).filter_by(
                match_id=match_id,
                team_id=match.away_team_id,
            ).first()
            
            result = {
                "match_id": match_id,
                "home_team": match.home_team.name,
                "away_team": match.away_team.name,
                "score": f"{match.home_score}-{match.away_score}",
                "home_stats": None,
                "away_stats": None,
            }
            
            # Format home team stats
            if home_stats:
                result["home_stats"] = {
                    "possession": home_stats.possession,
                    "shots": home_stats.shots,
                    "shots_on_target": home_stats.shots_on_target,
                    "passes": home_stats.passes,
                    "pass_accuracy": home_stats.pass_accuracy,
                    "tackles": home_stats.tackles,
                    "interceptions": home_stats.interceptions,
                    "fouls": home_stats.fouls,
                    "offsides": home_stats.offsides,
                    "corners": home_stats.corners,
                }
            
            # Format away team stats
            if away_stats:
                result["away_stats"] = {
                    "possession": away_stats.possession,
                    "shots": away_stats.shots,
                    "shots_on_target": away_stats.shots_on_target,
                    "passes": away_stats.passes,
                    "pass_accuracy": away_stats.pass_accuracy,
                    "tackles": away_stats.tackles,
                    "interceptions": away_stats.interceptions,
                    "fouls": away_stats.fouls,
                    "offsides": away_stats.offsides,
                    "corners": away_stats.corners,
                }
            
            return result
        
        except MatchNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to fetch match statistics",
                extra={"match_id": match_id, "error": str(e)}
            )
            raise DatabaseError("get_match_statistics", str(e))
    
    def trigger_sync(
        self,
        tournament_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Trigger manual synchronization of matches from SofaScore API.
        
        This is an administrative endpoint for manual syncs. For automatic
        synchronization, use Celery tasks.
        
        Args:
            tournament_id: ID of the tournament to sync.
            start_date: Start date for sync period.
            end_date: End date for sync period.
        
        Returns:
            Status dict with sync operation details.
        
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
            
            logger.info(
                f"Match sync triggered",
                extra={
                    "tournament_id": tournament_id,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
            
            # TODO: Call data_parser.sync_tournament_matches
            # from app.data_parser import sync_tournament_matches
            # sync_tournament_matches(self.db, tournament_id, start_date, end_date)
            
            return {
                "status": "success",
                "message": f"Synchronization triggered for tournament {tournament_id}",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
        
        except TournamentNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to trigger match sync",
                extra={
                    "tournament_id": tournament_id,
                    "error": str(e),
                }
            )
            raise DatabaseError("sync_matches", str(e))

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import Match, MatchStatistic
from app.schemas import Match as MatchSchema, MatchWithDetails
from app.exceptions import MatchNotFound, TournamentNotFound, DatabaseError
from app.services import BaseService
from app.repositories.match import MatchRepository
from app.repositories.tournament import TournamentRepository
from app.config import logger


class MatchService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repository = MatchRepository(db)
        self.tournament_repository = TournamentRepository(db)

    def get_by_id(self, match_id: int) -> MatchWithDetails:
        try:
            match = self.repository.find_by_id(match_id)

            if not match:
                logger.warning(
                    f"Match not found",
                    extra={"match_id": match_id}
                )
                raise MatchNotFound(match_id)

            return MatchWithDetails.from_orm(match)

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
        try:
            match = self.repository.find_by_id(match_id)

            if not match:
                raise MatchNotFound(match_id)

            statistics = self.repository.get_statistics(match_id)
            home_stats = None
            away_stats = None

            for stat in statistics:
                if stat.team_id == match.home_team_id:
                    home_stats = stat
                elif stat.team_id == match.away_team_id:
                    away_stats = stat

            result = {
                "match_id": match_id,
                "home_team": match.home_team.name,
                "away_team": match.away_team.name,
                "score": f"{match.home_score}-{match.away_score}",
                "home_stats": None,
                "away_stats": None,
            }

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


    def get_by_id_raw(self, match_id: int) -> Match:
        """Fetch ORM Match by ID, used internally.

        Args:
            match_id: ID of the match.

        Returns:
            Match ORM object.

        Raises:
            MatchNotFound: If match not found.
        """
        match = self.db.query(Match).filter_by(id=match_id).first()
        if not match:
            raise MatchNotFound(match_id)
        return match

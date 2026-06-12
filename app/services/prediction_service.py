"""
Service layer for match predictions using Poisson distribution.

Predicts match outcomes based on historical attacking and defensive strength
of both teams, using the classic Poisson regression model for football.
Home/away distinction is not applied — suitable for international tournaments
where all venues are effectively neutral.
"""

import math
import datetime
from typing import Dict, Any, Tuple

from sqlalchemy import func

from app.models import Team, Match
from app.exceptions import TeamNotFound, DatabaseError
from app.services import BaseService
from app.config import logger, MIN_HISTORICAL_MATCHES

DEFAULT_LEAGUE_AVG = 1.30
DECAY_FACTOR = 0.001
MAX_GOALS = 10
MIN_EXPECTED_GOALS = 0.20
MAX_EXPECTED_GOALS = 4.50


class PredictionService(BaseService):
    """Service for match prediction using Poisson distribution.

    Computes team attacking/defensive strength from historical finished matches,
    then calculates the probability of each possible scoreline using the
    independent Poisson model. Uses a single league average (no home/away
    distinction), suitable for international tournaments.
    """

    def predict(
        self,
        home_team_id: int,
        away_team_id: int,
    ) -> Dict[str, Any]:
        """Predict match outcome between two teams.

        Args:
            home_team_id: ID of the home team.
            away_team_id: ID of the away team.

        Returns:
            Dictionary with home_win/draw/away_win probabilities, most likely
            score, predicted goals, and confidence.

        Raises:
            TeamNotFound: If either team doesn't exist.
            DatabaseError: If data queries fail.
        """
        try:
            home_team = self.db.query(Team).filter_by(id=home_team_id).first()
            away_team = self.db.query(Team).filter_by(id=away_team_id).first()

            if not home_team:
                raise TeamNotFound(home_team_id)
            if not away_team:
                raise TeamNotFound(away_team_id)

            league_avg = self._get_league_average()

            reference_date = self._get_reference_date()

            home_attack, home_defense, home_sample = self._get_weighted_team_strengths(
                home_team_id,
                league_avg,
                reference_date,
            )
            away_attack, away_defense, away_sample = self._get_weighted_team_strengths(
                away_team_id,
                league_avg,
                reference_date,
            )

            home_strength = home_attack / league_avg if league_avg > 0 else 1.0
            away_def_strength = away_defense / league_avg if league_avg > 0 else 1.0
            away_strength = away_attack / league_avg if league_avg > 0 else 1.0
            home_def_strength = home_defense / league_avg if league_avg > 0 else 1.0

            lambda_home = self._clamp(
                league_avg * home_strength * away_def_strength,
                MIN_EXPECTED_GOALS,
                MAX_EXPECTED_GOALS,
            )
            lambda_away = self._clamp(
                league_avg * away_strength * home_def_strength,
                MIN_EXPECTED_GOALS,
                MAX_EXPECTED_GOALS,
            )

            home_win_prob = 0.0
            draw_prob = 0.0
            away_win_prob = 0.0

            max_prob = 0.0
            most_likely_home = 0
            most_likely_away = 0

            for h in range(MAX_GOALS + 1):
                for a in range(MAX_GOALS + 1):
                    prob = self._poisson(h, lambda_home) * self._poisson(a, lambda_away)
                    if prob > max_prob:
                        max_prob = prob
                        most_likely_home = h
                        most_likely_away = a
                    if h > a:
                        home_win_prob += prob
                    elif h == a:
                        draw_prob += prob
                    else:
                        away_win_prob += prob

            total = home_win_prob + draw_prob + away_win_prob
            if total > 0:
                home_win_prob = round(home_win_prob / total * 100, 1)
                draw_prob = round(draw_prob / total * 100, 1)
                away_win_prob = round(away_win_prob / total * 100, 1)
            over_25_prob = round(
                self._over_25_probability(lambda_home + lambda_away) * 100,
                1,
            )

            confidence = self._calculate_confidence(home_sample, away_sample)

            logger.info(
                f"Prediction computed",
                extra={
                    "home_team": home_team.name,
                    "away_team": away_team.name,
                    "league_avg": round(league_avg, 2),
                    "lambda_home": round(lambda_home, 2),
                    "lambda_away": round(lambda_away, 2),
                    "home_effective_matches": round(home_sample, 2),
                    "away_effective_matches": round(away_sample, 2),
                    "home_win": home_win_prob,
                    "draw": draw_prob,
                    "away_win": away_win_prob,
                },
            )

            return {
                "home_team": home_team.name,
                "away_team": away_team.name,
                "home_team_id": home_team.id,
                "away_team_id": away_team.id,
                "home_win_probability": home_win_prob,
                "draw_probability": draw_prob,
                "away_win_probability": away_win_prob,
                "over_25_probability": over_25_prob,
                "most_likely_score": (
                    f"{most_likely_home}-{most_likely_away}"
                ),
                "predicted_home_goals": round(lambda_home, 2),
                "predicted_away_goals": round(lambda_away, 2),
                "confidence": confidence,
            }

        except TeamNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to compute prediction",
                extra={
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "error": str(e),
                },
            )
            raise DatabaseError("predict", str(e))

    def _get_league_average(self) -> float:
        """Calculate league average goals per team per match.

        Uses all finished matches with exponential recency weighting to compute
        a single average. Home/away distinction is not used, which fits neutral
        international tournaments better than a domestic home advantage model.

        Returns:
            Average goals scored per team per match.
        """
        try:
            reference_date = self._get_reference_date()
            matches = self.db.query(
                Match.home_score,
                Match.away_score,
                Match.match_date,
            ).filter(
                Match.status == "finished",
                Match.home_score.isnot(None),
                Match.away_score.isnot(None),
            ).all()

            weighted_goals = 0.0
            weighted_team_matches = 0.0

            for home_score, away_score, match_date in matches:
                weight = self._match_weight(match_date, reference_date)
                weighted_goals += (home_score + away_score) * weight
                weighted_team_matches += 2.0 * weight

            if weighted_team_matches == 0:
                return DEFAULT_LEAGUE_AVG

            return weighted_goals / weighted_team_matches
        except Exception as e:
            logger.warning(
                f"Failed to compute league average, using default",
                extra={"error": str(e)},
            )
            return DEFAULT_LEAGUE_AVG

    def _get_weighted_team_strengths(
        self,
        team_id: int,
        league_avg: float,
        reference_date: datetime.date,
        decay_factor: float = DECAY_FACTOR,
    ) -> Tuple[float, float, float]:
        """Calculate weighted attacking and defensive strength for a team.

        Uses all historical matches (home and away) with exponential time decay
        so recent matches contribute more to the estimate. Raw team rates are
        shrunk toward the global average so teams with few recent games do not
        produce extreme predictions.

        Args:
            team_id: ID of the team.
            league_avg: Global goals per team per match average.
            reference_date: Latest available match date used as recency anchor.
            decay_factor: Exponential decay factor per day (default 0.001).

        Returns:
            Tuple of (attack_strength, defense_strength, effective_matches).
        """
        try:
            matches = self.db.query(Match).filter(
                (Match.home_team_id == team_id) | (Match.away_team_id == team_id),
                Match.status == "finished",
                Match.home_score.isnot(None),
                Match.away_score.isnot(None),
            ).all()

            total_weight = 0.0
            weighted_goals_for = 0.0
            weighted_goals_against = 0.0

            for match in matches:
                weight = self._match_weight(match.match_date, reference_date, decay_factor)
                total_weight += weight

                if match.home_team_id == team_id:
                    weighted_goals_for += match.home_score * weight
                    weighted_goals_against += match.away_score * weight
                else:
                    weighted_goals_for += match.away_score * weight
                    weighted_goals_against += match.home_score * weight

            if total_weight == 0:
                return league_avg, league_avg, 0.0

            raw_attack = weighted_goals_for / total_weight
            raw_defense = weighted_goals_against / total_weight
            prior_matches = max(MIN_HISTORICAL_MATCHES, 1)
            sample_weight = total_weight / (total_weight + prior_matches)

            attack = league_avg + (raw_attack - league_avg) * sample_weight
            defense = league_avg + (raw_defense - league_avg) * sample_weight

            return max(attack, 0.05), max(defense, 0.05), total_weight
        except Exception as e:
            logger.warning(
                f"Failed to compute weighted team strengths",
                extra={"team_id": team_id, "error": str(e)},
            )
            return league_avg, league_avg, 0.0

    def _get_reference_date(self) -> datetime.date:
        """Use the latest finished match date as the recency anchor.

        Anchoring to the dataset avoids silently decaying all historical matches
        as calendar time passes without a fresh import.
        """
        try:
            latest_match_date = self.db.query(
                func.max(Match.match_date)
            ).filter(
                Match.status == "finished",
                Match.home_score.isnot(None),
                Match.away_score.isnot(None),
            ).scalar()

            if latest_match_date:
                return latest_match_date.date()
        except Exception as e:
            logger.warning(
                f"Failed to get prediction reference date, using today",
                extra={"error": str(e)},
            )

        return datetime.date.today()

    def _match_weight(
        self,
        match_date: datetime.datetime,
        reference_date: datetime.date,
        decay_factor: float = DECAY_FACTOR,
    ) -> float:
        """Calculate exponential recency weight for a match."""
        if match_date is None:
            return 0.0

        days_ago = (reference_date - match_date.date()).days
        return math.exp(-decay_factor * max(days_ago, 0))

    def _poisson(self, k: int, lam: float) -> float:
        """Poisson probability mass function: P(X = k) for given lambda.

        Args:
            k: Number of events (goals).
            lam: Expected number of events (lambda).

        Returns:
            Probability of exactly k events occurring.
        """
        return (lam ** k) * math.exp(-lam) / math.factorial(k)

    def _over_25_probability(self, total_goals_lambda: float) -> float:
        """Probability that total match goals exceed 2.5."""
        under_or_equal_2 = sum(
            self._poisson(goals, total_goals_lambda)
            for goals in range(3)
        )
        return self._clamp(1.0 - under_or_equal_2, 0.0, 1.0)

    def _calculate_confidence(
        self,
        home_effective_matches: float,
        away_effective_matches: float,
    ) -> float:
        """Calculate prediction confidence based on available data.

        Confidence increases with balanced, recent historical data for both
        teams. Uses effective matches after recency weighting, not raw counts.

        Args:
            home_effective_matches: Weighted historical matches for home team.
            away_effective_matches: Weighted historical matches for away team.

        Returns:
            Confidence percentage (0-95).
        """
        try:
            if home_effective_matches <= 0 or away_effective_matches <= 0:
                return 10.0

            required = max(MIN_HISTORICAL_MATCHES, 1)
            weaker_sample = min(home_effective_matches, away_effective_matches)
            stronger_sample = max(home_effective_matches, away_effective_matches)
            balanced_sample_ratio = weaker_sample / stronger_sample

            team_floor = min(weaker_sample / required, 1.0)
            total_depth = min(
                (home_effective_matches + away_effective_matches) / (required * 4),
                1.0,
            )

            confidence = 15.0 + (50.0 * team_floor) + (30.0 * total_depth)
            confidence *= 0.85 + (0.15 * balanced_sample_ratio)

            return round(self._clamp(confidence, 10.0, 95.0), 1)
        except Exception:
            return 30.0

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        """Clamp a float between lower and upper bounds."""
        return max(lower, min(value, upper))

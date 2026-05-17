"""
Service layer for match predictions using Poisson distribution.

Predicts match outcomes based on historical attacking and defensive strength
of both teams, using the classic Poisson regression model for football.
"""

import math
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models import Team, Match
from app.exceptions import TeamNotFound, DatabaseError
from app.services import BaseService
from app.config import logger, MIN_HISTORICAL_MATCHES

MAX_GOALS = 6


class PredictionService(BaseService):
    """Service for match prediction using Poisson distribution.

    Computes team attacking/defensive strength from historical finished matches,
    then calculates the probability of each possible scoreline using the
    independent Poisson model.
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

            league_avg_home, league_avg_away = self._get_league_averages()

            home_attack, home_defense = self._get_team_strengths(
                home_team_id, is_home=True
            )
            away_attack, away_defense = self._get_team_strengths(
                away_team_id, is_home=False
            )

            avg_attack = (league_avg_home + league_avg_away) / 2
            avg_defense = avg_attack

            home_strength = home_attack / avg_attack if avg_attack > 0 else 1.0
            away_def_strength = away_defense / avg_defense if avg_defense > 0 else 1.0
            away_strength = away_attack / avg_attack if avg_attack > 0 else 1.0
            home_def_strength = home_defense / avg_defense if avg_defense > 0 else 1.0

            lambda_home = league_avg_home * home_strength * away_def_strength
            lambda_away = league_avg_away * away_strength * home_def_strength

            lambda_home = max(lambda_home, 0.1)
            lambda_away = max(lambda_away, 0.1)

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

            confidence = self._calculate_confidence(home_team_id, away_team_id)

            logger.info(
                f"Prediction computed",
                extra={
                    "home_team": home_team.name,
                    "away_team": away_team.name,
                    "lambda_home": round(lambda_home, 2),
                    "lambda_away": round(lambda_away, 2),
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

    def _get_league_averages(self) -> Tuple[float, float]:
        """Calculate league average goals per match for home and away teams.

        Returns:
            Tuple of (avg_home_goals, avg_away_goals) across all finished matches.
        """
        try:
            result = self.db.query(
                func.avg(Match.home_score).label("avg_home"),
                func.avg(Match.away_score).label("avg_away"),
            ).filter(
                Match.status == "finished",
                Match.home_score.isnot(None),
                Match.away_score.isnot(None),
            ).first()

            avg_home = float(result.avg_home) if result and result.avg_home else 1.5
            avg_away = float(result.avg_away) if result and result.avg_away else 1.1

            return avg_home, avg_away
        except Exception as e:
            logger.warning(
                f"Failed to compute league averages, using defaults",
                extra={"error": str(e)},
            )
            return 1.5, 1.1

    def _get_team_strengths(
        self,
        team_id: int,
        is_home: bool,
    ) -> Tuple[float, float]:
        """Calculate attacking and defensive strength for a team.

        Attack strength = avg goals scored by the team (home or away).
        Defense strength = avg goals conceded by the team (home or away).

        Args:
            team_id: ID of the team.
            is_home: True for home stats, False for away stats.

        Returns:
            Tuple of (attack_strength, defense_strength).
        """
        try:
            if is_home:
                matches = self.db.query(Match).filter(
                    Match.home_team_id == team_id,
                    Match.status == "finished",
                    Match.home_score.isnot(None),
                    Match.away_score.isnot(None),
                ).all()
                goals_for = [m.home_score for m in matches]
                goals_against = [m.away_score for m in matches]
            else:
                matches = self.db.query(Match).filter(
                    Match.away_team_id == team_id,
                    Match.status == "finished",
                    Match.home_score.isnot(None),
                    Match.away_score.isnot(None),
                ).all()
                goals_for = [m.away_score for m in matches]
                goals_against = [m.home_score for m in matches]

            n = len(goals_for)
            if n == 0:
                return 1.0, 1.0

            attack = sum(goals_for) / n
            defense = sum(goals_against) / n

            return attack, defense
        except Exception as e:
            logger.warning(
                f"Failed to compute team strengths",
                extra={"team_id": team_id, "is_home": is_home, "error": str(e)},
            )
            return 1.0, 1.0

    def _poisson(self, k: int, lam: float) -> float:
        """Poisson probability mass function: P(X = k) for given lambda.

        Args:
            k: Number of events (goals).
            lam: Expected number of events (lambda).

        Returns:
            Probability of exactly k events occurring.
        """
        return (lam ** k) * math.exp(-lam) / math.factorial(k)

    def _calculate_confidence(self, home_team_id: int, away_team_id: int) -> float:
        """Calculate prediction confidence based on available data.

        Confidence increases with more historical matches available.
        Caps at 95% for abundant data.

        Args:
            home_team_id: ID of the home team.
            away_team_id: ID of the away team.

        Returns:
            Confidence percentage (0-95).
        """
        try:
            home_matches = self.db.query(Match).filter(
                (Match.home_team_id == home_team_id) | (Match.away_team_id == home_team_id),
                Match.status == "finished",
            ).count()

            away_matches = self.db.query(Match).filter(
                (Match.home_team_id == away_team_id) | (Match.away_team_id == away_team_id),
                Match.status == "finished",
            ).count()

            total_matches = home_matches + away_matches
            required = MIN_HISTORICAL_MATCHES * 2

            if total_matches >= required * 2:
                return 95.0
            elif total_matches >= required:
                return 75.0
            elif total_matches >= MIN_HISTORICAL_MATCHES:
                return 50.0
            else:
                return max(10.0, (total_matches / required) * 50.0)
        except Exception:
            return 30.0

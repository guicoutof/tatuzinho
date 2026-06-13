"""
Database maintenance routines derived from imported match data.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal


def sync_tournament_teams(db: Session) -> None:
    db.execute(
        text(
            """
            INSERT INTO tournament_teams (tournament_id, team_id)
            SELECT DISTINCT tournament_id, team_id
            FROM (
                SELECT tournament_id, home_team_id AS team_id
                FROM matches
                WHERE tournament_id IS NOT NULL AND home_team_id IS NOT NULL
                UNION
                SELECT tournament_id, away_team_id AS team_id
                FROM matches
                WHERE tournament_id IS NOT NULL AND away_team_id IS NOT NULL
            ) AS pairs
            ON CONFLICT DO NOTHING
            """
        )
    )


def recalculate_team_stats(db: Session) -> None:
    db.execute(
        text(
            """
            UPDATE teams
            SET
                matches_played = 0,
                wins = 0,
                draws = 0,
                losses = 0,
                goals_for = 0,
                goals_against = 0,
                goal_difference = 0,
                points = 0
            """
        )
    )

    db.execute(
        text(
            """
            WITH team_results AS (
                SELECT
                    home_team_id AS team_id,
                    home_score AS goals_for,
                    away_score AS goals_against,
                    CASE WHEN home_score > away_score THEN 1 ELSE 0 END AS win,
                    CASE WHEN home_score = away_score THEN 1 ELSE 0 END AS draw,
                    CASE WHEN home_score < away_score THEN 1 ELSE 0 END AS loss
                FROM matches
                WHERE status = 'finished'
                    AND home_score IS NOT NULL
                    AND away_score IS NOT NULL
                    AND home_team_id IS NOT NULL

                UNION ALL

                SELECT
                    away_team_id AS team_id,
                    away_score AS goals_for,
                    home_score AS goals_against,
                    CASE WHEN away_score > home_score THEN 1 ELSE 0 END AS win,
                    CASE WHEN away_score = home_score THEN 1 ELSE 0 END AS draw,
                    CASE WHEN away_score < home_score THEN 1 ELSE 0 END AS loss
                FROM matches
                WHERE status = 'finished'
                    AND home_score IS NOT NULL
                    AND away_score IS NOT NULL
                    AND away_team_id IS NOT NULL
            ),
            aggregate_stats AS (
                SELECT
                    team_id,
                    COUNT(*) AS matches_played,
                    COALESCE(SUM(win), 0) AS wins,
                    COALESCE(SUM(draw), 0) AS draws,
                    COALESCE(SUM(loss), 0) AS losses,
                    COALESCE(SUM(goals_for), 0) AS goals_for,
                    COALESCE(SUM(goals_against), 0) AS goals_against
                FROM team_results
                GROUP BY team_id
            )
            UPDATE teams
            SET
                matches_played = aggregate_stats.matches_played,
                wins = aggregate_stats.wins,
                draws = aggregate_stats.draws,
                losses = aggregate_stats.losses,
                goals_for = aggregate_stats.goals_for,
                goals_against = aggregate_stats.goals_against,
                goal_difference = aggregate_stats.goals_for - aggregate_stats.goals_against,
                points = aggregate_stats.wins * 3 + aggregate_stats.draws
            FROM aggregate_stats
            WHERE teams.id = aggregate_stats.team_id
            """
        )
    )


def recalculate_player_stats(db: Session) -> None:
    db.execute(
        text(
            """
            UPDATE players
            SET
                matches_played = 0,
                goals = 0,
                assists = 0,
                yellow_cards = 0,
                red_cards = 0
            """
        )
    )

    db.execute(
        text(
            """
            WITH aggregate_stats AS (
                SELECT
                    player_id,
                    COUNT(DISTINCT match_id) AS matches_played,
                    COALESCE(SUM(goals), 0) AS goals,
                    COALESCE(SUM(assists), 0) AS assists,
                    COALESCE(SUM(yellow_cards), 0) AS yellow_cards,
                    COALESCE(SUM(red_cards), 0) AS red_cards
                FROM match_statistics
                WHERE player_id IS NOT NULL
                GROUP BY player_id
            )
            UPDATE players
            SET
                matches_played = aggregate_stats.matches_played,
                goals = aggregate_stats.goals,
                assists = aggregate_stats.assists,
                yellow_cards = aggregate_stats.yellow_cards,
                red_cards = aggregate_stats.red_cards
            FROM aggregate_stats
            WHERE players.id = aggregate_stats.player_id
            """
        )
    )


def maintain_database(db: Session) -> None:
    sync_tournament_teams(db)
    recalculate_team_stats(db)
    recalculate_player_stats(db)


def run_maintenance() -> None:
    db = SessionLocal()
    try:
        maintain_database(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_maintenance()

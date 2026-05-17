"""
Importer for StatsBomb Open Data.

Reads StatsBomb JSON files and populates the database with national team
matches, teams, players, and tournaments.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Auto-detect venv if running outside it
_venv_path = os.path.join(os.path.dirname(__file__), "..", "venv", "lib", "python3.12", "site-packages")
if os.path.isdir(_venv_path) and _venv_path not in sys.path:
    sys.path.insert(0, _venv_path)

from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal

logger = logging.getLogger(__name__)

OPEN_DATA_DIR = os.path.expanduser(
    "~/Documentos/Projetos/open-data"
)

COMPETITION_SEASONS: Dict[int, List[int]] = {
    43: [3, 106],
    55: [43, 282],
    223: [282],
    1267: [107],
}

COMPETITION_META: Dict[int, Dict[str, Any]] = {
    43: {"type": "worldcup", "country": "International"},
    55: {"type": "euro", "country": "Europe"},
    223: {"type": "copa_america", "country": "South America"},
    1267: {"type": "afcon", "country": "Africa"},
}

STAGE_PHASE_MAP: Dict[str, str] = {
    "Group Stage": "group",
    "Round of 16": "round_of_16",
    "Round of 32": "round_of_32",
    "Quarter-finals": "quarter",
    "Semi-finals": "semi",
    "Final": "final",
    "Third-place match": "third_place",
    "Play-off for third place": "third_place",
    "Third-Place match": "third_place",
}


class StatsBombImporter:
    def __init__(self, db: Session):
        self.db = db
        self.stats = {"tournaments": 0, "teams": 0, "matches": 0, "players": 0}
        self._team_cache: Dict[int, models.Team] = {}
        self._player_cache: Dict[int, models.Player] = {}
        self._match_ids: set = set()
        self._load_caches()

    def _load_caches(self):
        for t in self.db.query(models.Team).filter(models.Team.source == "statsbomb").all():
            self._team_cache[t.source_id] = t
        for p in self.db.query(models.Player).filter(models.Player.source == "statsbomb").all():
            self._player_cache[p.source_id] = p
        for m in self.db.query(models.Match.source_id).filter(models.Match.source == "statsbomb").all():
            self._match_ids.add(m.source_id)
        logger.info(f"Loaded {len(self._team_cache)} teams, {len(self._player_cache)} players, {len(self._match_ids)} matches from DB")

    def load_json(self, path: str) -> Any:
        with open(path, "r") as f:
            return json.load(f)

    def import_all(self) -> Dict[str, int]:
        competitions = self.load_json(
            os.path.join(OPEN_DATA_DIR, "data", "competitions.json")
        )

        for comp in competitions:
            comp_id = comp["competition_id"]
            season_id = comp["season_id"]
            season_name = comp["season_name"]

            if comp_id not in COMPETITION_SEASONS:
                continue
            if season_id not in COMPETITION_SEASONS[comp_id]:
                continue

            year = int(season_name)
            if year < 2010:
                continue

            logger.info(
                f"Importing {comp['competition_name']} {season_name} "
                f"(comp={comp_id}, season={season_id})"
            )
            self._import_competition(comp_id, season_id, comp)
            self.db.commit()
            logger.info(f"  Committed. Running totals - Teams: {self.stats['teams']}, Matches: {self.stats['matches']}, Players: {self.stats['players']}")

        return self.stats

    def _import_competition(
        self, comp_id: int, season_id: int, comp_data: Dict[str, Any]
    ):
        tournament = self._get_or_create_tournament(comp_id, season_id, comp_data)
        matches_path = os.path.join(
            OPEN_DATA_DIR, "data", "matches", str(comp_id), f"{season_id}.json"
        )

        if not os.path.exists(matches_path):
            logger.warning(f"Matches file not found: {matches_path}")
            return

        matches_data = self.load_json(matches_path)

        total = len(matches_data)
        for i, match_data in enumerate(matches_data):
            if i > 0 and i % 10 == 0:
                logger.info(f"  [{i}/{total}] matches imported...")
            self._import_match(tournament, match_data)

    def _get_or_create_tournament(
        self, comp_id: int, season_id: int, comp_data: Dict[str, Any]
    ) -> models.Tournament:
        source_id = f"{comp_id}_{season_id}"
        existing = (
            self.db.query(models.Tournament)
            .filter(
                models.Tournament.source_id == source_id,
                models.Tournament.source == "statsbomb",
            )
            .first()
        )
        if existing:
            return existing

        name = comp_data["competition_name"]
        season_name = comp_data["season_name"]
        meta = COMPETITION_META.get(comp_id, {})

        tournament = models.Tournament(
            source_id=source_id,
            source="statsbomb",
            name=name,
            slug=f"{name.lower().replace(' ', '-')}-{season_name}",
            season=int(season_name),
            type=meta.get("type", "international"),
            country=meta.get("country"),
        )
        self.db.add(tournament)
        self.db.flush()
        self.stats["tournaments"] += 1
        return tournament

    def _get_or_create_team(self, team_id: int, team_name: str) -> models.Team:
        cached = self._team_cache.get(team_id)
        if cached:
            return cached

        code = team_name[:3].upper()

        team = models.Team(
            source_id=team_id,
            source="statsbomb",
            name=team_name,
            code=code,
            country=team_name,
        )
        self.db.add(team)
        self.db.flush()
        self._team_cache[team_id] = team
        self.stats["teams"] += 1
        return team

    def _import_match(
        self, tournament: models.Tournament, match_data: Dict[str, Any]
    ):
        match_id = match_data["match_id"]

        if match_id in self._match_ids:
            return

        home_data = match_data["home_team"]
        away_data = match_data["away_team"]

        home_team = self._get_or_create_team(
            home_data["home_team_id"], home_data["home_team_name"]
        )
        away_team = self._get_or_create_team(
            away_data["away_team_id"], away_data["away_team_name"]
        )

        match_date_str = match_data["match_date"]
        kick_off = match_data.get("kick_off", "00:00:00.000")
        match_date = datetime.fromisoformat(f"{match_date_str}T{kick_off}")

        stage_name = match_data.get("competition_stage", {}).get("name", "")
        phase = STAGE_PHASE_MAP.get(stage_name)

        home_group = home_data.get("home_team_group")
        away_group = away_data.get("away_team_group")
        group = home_group or away_group

        match = models.Match(
            source_id=match_id,
            source="statsbomb",
            tournament_id=tournament.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=match_date,
            status="finished",
            home_score=match_data.get("home_score"),
            away_score=match_data.get("away_score"),
            group=group,
            phase=phase,
            venue=match_data.get("stadium", {}).get("name"),
            city=match_data.get("stadium", {}).get("country", {}).get("name"),
        )
        self.db.add(match)
        self.db.flush()
        self.stats["matches"] += 1

        self._import_lineups(match_id, home_team, away_team)

    def _import_lineups(
        self, match_id: int, home_team: models.Team, away_team: models.Team
    ):
        lineup_path = os.path.join(
            OPEN_DATA_DIR, "data", "lineups", f"{match_id}.json"
        )
        if not os.path.exists(lineup_path):
            return

        lineups = self.load_json(lineup_path)
        for lineup_data in lineups:
            team_id = lineup_data["team_id"]
            team = home_team if team_id == home_team.source_id else away_team

            for player_data in lineup_data.get("lineup", []):
                self._get_or_create_player(player_data, team)

    def _get_or_create_player(
        self, player_data: Dict[str, Any], team: models.Team
    ) -> models.Player:
        player_id = player_data["player_id"]
        cached = self._player_cache.get(player_id)
        if cached:
            return cached

        position = self._map_position(player_data.get("positions", []))

        player = models.Player(
            source_id=player_id,
            source="statsbomb",
            name=player_data["player_name"],
            position=position,
            number=player_data.get("jersey_number"),
            team_id=team.id,
        )
        self.db.add(player)
        self.db.flush()
        self._player_cache[player_id] = player
        self.stats["players"] += 1
        return player

    @staticmethod
    def _map_position(positions: List[Dict[str, Any]]) -> str:
        if not positions:
            return "MID"
        pos_name = positions[0].get("position", "")
        pos_lower = pos_name.lower()
        if "goalkeeper" in pos_lower:
            return "GK"
        if "back" in pos_lower or "defender" in pos_lower:
            return "DEF"
        if "midfield" in pos_lower:
            return "MID"
        if "forward" in pos_lower or "striker" in pos_lower or "wing" in pos_lower:
            return "FWD"
        return "MID"


def run_import():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    db = SessionLocal()
    try:
        importer = StatsBombImporter(db)
        stats = importer.import_all()
        logger.info(
            f"Import completed! "
            f"Tournaments: {stats['tournaments']}, "
            f"Teams: {stats['teams']}, "
            f"Matches: {stats['matches']}, "
            f"Players: {stats['players']}"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Import failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_import()

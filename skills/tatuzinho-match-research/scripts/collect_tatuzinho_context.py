#!/usr/bin/env python3
"""Collect a compact Tatuzinho context packet for two teams."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


def normalize(value: str | None) -> str:
    if not value:
        return ""
    return (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .lower()
    )


def get_json(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    url = base_url.rstrip("/") + path + query
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return json.loads(response.read().decode(charset))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{url} returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc


def resolve_team(teams: list[dict[str, Any]], query: str) -> dict[str, Any]:
    wanted = normalize(query)
    matches: list[dict[str, Any]] = []
    for team in teams:
        candidates = [
            str(team.get("id", "")),
            team.get("name", ""),
            team.get("name_pt_br", ""),
            team.get("code", ""),
        ]
        normalized = [normalize(str(candidate)) for candidate in candidates if candidate]
        if wanted in normalized:
            return team
        if any(wanted and wanted in candidate for candidate in normalized):
            matches.append(team)

    if len(matches) == 1:
        return matches[0]
    if matches:
        options = ", ".join(
            f"{team.get('id')}:{team.get('name')}({team.get('code')})"
            for team in matches[:10]
        )
        raise RuntimeError(f"Ambiguous team '{query}'. Matches: {options}")
    raise RuntimeError(f"Team '{query}' was not found in /api/v1/teams/")


def slim_players(team_detail: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    players = team_detail.get("players") or []
    slimmed = []
    for player in players[:limit]:
        stats = player.get("stats") or {}
        slimmed.append(
            {
                "id": player.get("id"),
                "name": player.get("name"),
                "position": player.get("position"),
                "number": player.get("number"),
                "nationality": player.get("nationality"),
                "stats": {
                    "matches_played": stats.get("matches_played"),
                    "goals": stats.get("goals"),
                    "assists": stats.get("assists"),
                    "yellow_cards": stats.get("yellow_cards"),
                    "red_cards": stats.get("red_cards"),
                },
            }
        )
    return slimmed


def compact_team(team_detail: dict[str, Any], analytics: Any, recent: Any, player_limit: int) -> dict[str, Any]:
    return {
        "id": team_detail.get("id"),
        "name": team_detail.get("name"),
        "code": team_detail.get("code"),
        "country": team_detail.get("country"),
        "stats": team_detail.get("stats"),
        "analytics": analytics,
        "recent_matches": recent,
        "players": slim_players(team_detail, player_limit),
    }


def collect(args: argparse.Namespace) -> dict[str, Any]:
    teams = get_json(args.base_url, "/api/v1/teams/")
    home = resolve_team(teams, args.home)
    away = resolve_team(teams, args.away)

    home_id = int(home["id"])
    away_id = int(away["id"])

    home_detail = get_json(args.base_url, f"/api/v1/teams/{home_id}")
    away_detail = get_json(args.base_url, f"/api/v1/teams/{away_id}")
    home_analytics = get_json(args.base_url, f"/api/v1/teams/{home_id}/analytics")
    away_analytics = get_json(args.base_url, f"/api/v1/teams/{away_id}/analytics")
    home_recent = get_json(
        args.base_url,
        f"/api/v1/teams/{home_id}/recent-matches",
        {"limit": args.recent_limit},
    )
    away_recent = get_json(
        args.base_url,
        f"/api/v1/teams/{away_id}/recent-matches",
        {"limit": args.recent_limit},
    )
    comparison = get_json(args.base_url, f"/api/v1/analytics/comparison/{home_id}/{away_id}")
    prediction = get_json(
        args.base_url,
        "/api/v1/predictions/predict",
        {"home_team_id": home_id, "away_team_id": away_id},
    )

    packet = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url.rstrip("/"),
        "input": {"home": args.home, "away": args.away},
        "resolved": {
            "home": home,
            "away": away,
        },
        "prediction": prediction,
        "head_to_head": comparison,
        "teams": {
            "home": compact_team(home_detail, home_analytics, home_recent, args.player_limit),
            "away": compact_team(away_detail, away_analytics, away_recent, args.player_limit),
        },
    }

    if args.raw:
        packet["raw"] = {
            "home_detail": home_detail,
            "away_detail": away_detail,
            "home_analytics": home_analytics,
            "away_analytics": away_analytics,
            "home_recent": home_recent,
            "away_recent": away_recent,
            "comparison": comparison,
            "prediction": prediction,
        }
    return packet


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect Tatuzinho prediction, team, player and history context for two teams."
    )
    parser.add_argument("--home", required=True, help="Home team name, code, Portuguese alias, or ID.")
    parser.add_argument("--away", required=True, help="Away team name, code, Portuguese alias, or ID.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Tatuzinho API base URL.")
    parser.add_argument("--recent-limit", type=int, default=8, help="Recent matches per team.")
    parser.add_argument("--player-limit", type=int, default=20, help="Players per team in compact output.")
    parser.add_argument("--raw", action="store_true", help="Include full endpoint payloads.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        packet = collect(args)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(packet, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

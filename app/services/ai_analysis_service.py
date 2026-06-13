"""
AI-assisted match analysis service.

Combines local database analytics with a web-enabled OpenAI Responses API call
to produce an updated, explainable match preview.
"""

import datetime
import json
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy import func

from app.config import (
    AI_ANALYSIS_MODEL,
    AI_ANALYSIS_TIMEOUT_SECONDS,
    AI_WEB_SEARCH_ENABLED,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    logger,
)
from app.exceptions import DatabaseError, TeamNotFound
from app.models import Match, Player, Team
from app.schemas import PredictionResponse
from app.services import BaseService
from app.services.analytics_service import AnalyticsService
from app.services.prediction_service import PredictionService
from app.services.team_service import TeamService


class AIAnalysisService(BaseService):
    """Build enriched match analysis from local data plus recent web context."""

    def __init__(self, db):
        super().__init__(db)
        self.prediction_service = PredictionService(db)
        self.team_service = TeamService(db)
        self.analytics_service = AnalyticsService(db)

    def analyze_match(
        self,
        home_team_id: int,
        away_team_id: int,
        include_web: bool = True,
    ) -> Dict[str, Any]:
        """Generate an AI-enriched analysis for a match.

        Args:
            home_team_id: Home team ID.
            away_team_id: Away team ID.
            include_web: Whether the model may use web search.

        Returns:
            Analysis payload with prediction, local context, AI status, and sources.

        Raises:
            TeamNotFound: If either team does not exist.
            DatabaseError: If local database context cannot be built.
        """
        try:
            home_team = self.db.query(Team).filter_by(id=home_team_id).first()
            away_team = self.db.query(Team).filter_by(id=away_team_id).first()

            if not home_team:
                raise TeamNotFound(home_team_id)
            if not away_team:
                raise TeamNotFound(away_team_id)

            prediction = self.prediction_service.predict(home_team_id, away_team_id)
            local_context = self._build_local_context(
                home_team,
                away_team,
                prediction,
            )

            if not OPENAI_API_KEY:
                return self._build_response(
                    home_team,
                    away_team,
                    prediction,
                    local_context,
                    ai_status="disabled",
                    ai_error="OPENAI_API_KEY is not configured",
                )

            try:
                ai_result = self._call_openai_agent(local_context, include_web)
                return self._build_response(
                    home_team,
                    away_team,
                    prediction,
                    local_context,
                    ai_status="completed",
                    analysis=ai_result["analysis"],
                    web_sources=ai_result["sources"],
                )
            except Exception as e:
                logger.warning(
                    "AI analysis failed; returning local fallback",
                    extra={
                        "home_team_id": home_team_id,
                        "away_team_id": away_team_id,
                        "error": str(e),
                    },
                )
                return self._build_response(
                    home_team,
                    away_team,
                    prediction,
                    local_context,
                    ai_status="error",
                    ai_error=str(e),
                )

        except TeamNotFound:
            raise
        except Exception as e:
            logger.error(
                "Failed to build match analysis",
                extra={
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "error": str(e),
                },
            )
            raise DatabaseError("analyze_match", str(e))

    def _build_local_context(
        self,
        home_team: Team,
        away_team: Team,
        prediction: Dict[str, Any],
    ) -> Dict[str, Any]:
        latest_match_date = self.db.query(func.max(Match.match_date)).filter(
            Match.status == "finished",
            Match.home_score.isnot(None),
            Match.away_score.isnot(None),
        ).scalar()

        return {
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "dataset": {
                "source": "StatsBomb Open Data imported into Tatuzinho",
                "latest_finished_match_date": latest_match_date,
                "note": (
                    "Historical database data may lag real-world squads, injuries, "
                    "fixtures, and news."
                ),
            },
            "teams": {
                "home": self._team_snapshot(home_team),
                "away": self._team_snapshot(away_team),
            },
            "prediction": prediction,
            "recent_matches": {
                "home": self.team_service.get_recent_matches(home_team.id, limit=5),
                "away": self.team_service.get_recent_matches(away_team.id, limit=5),
            },
            "team_analytics": {
                "home": self.team_service.get_analytics(home_team.id),
                "away": self.team_service.get_analytics(away_team.id),
            },
            "head_to_head": self.analytics_service.compare_teams(
                home_team.id,
                away_team.id,
            ),
            "top_players": {
                "home": self._top_players(home_team.id),
                "away": self._top_players(away_team.id),
            },
        }

    def _team_snapshot(self, team: Team) -> Dict[str, Any]:
        return {
            "id": team.id,
            "name": team.name,
            "code": team.code,
            "country": team.country,
            "matches_played": team.matches_played,
            "wins": team.wins,
            "draws": team.draws,
            "losses": team.losses,
            "goals_for": team.goals_for,
            "goals_against": team.goals_against,
            "goal_difference": team.goal_difference,
        }

    def _top_players(self, team_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        players = self.db.query(Player).filter(
            Player.team_id == team_id,
        ).order_by(
            Player.goals.desc(),
            Player.assists.desc(),
            Player.matches_played.desc(),
        ).limit(limit).all()

        return [
            {
                "id": player.id,
                "name": player.name,
                "position": player.position,
                "matches_played": player.matches_played,
                "goals": player.goals,
                "assists": player.assists,
            }
            for player in players
        ]

    def _call_openai_agent(
        self,
        local_context: Dict[str, Any],
        include_web: bool,
    ) -> Dict[str, Any]:
        payload = {
            "model": AI_ANALYSIS_MODEL,
            "input": [
                {
                    "role": "system",
                    "content": self._system_prompt(),
                },
                {
                    "role": "user",
                    "content": (
                        "Analise esta partida usando primeiro os dados locais do "
                        "Tatuzinho. Quando a busca web estiver disponivel, complemente "
                        "com noticias recentes sobre convocacoes, lesoes, fase atual, "
                        "calendario e contexto competitivo. Responda apenas no JSON "
                        "definido pelo schema.\n\n"
                        + json.dumps(local_context, default=str, ensure_ascii=False)
                    ),
                },
            ],
            "text": {"format": self._response_format_schema()},
        }

        if include_web and AI_WEB_SEARCH_ENABLED:
            payload["tools"] = [{"type": "web_search"}]
            payload["include"] = ["web_search_call.action.sources"]

        response = requests.post(
            f"{OPENAI_BASE_URL.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=AI_ANALYSIS_TIMEOUT_SECONDS,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"OpenAI API returned {response.status_code}: {response.text[:500]}"
            )

        response_payload = response.json()
        output_text = self._extract_output_text(response_payload)
        if not output_text:
            raise RuntimeError("OpenAI API returned no analysis text")

        analysis = json.loads(output_text)
        sources = self._merge_sources(
            analysis.get("fontes_consultadas", []),
            self._extract_openai_sources(response_payload),
        )

        analysis["fontes_consultadas"] = sources
        return {"analysis": analysis, "sources": sources}

    def _system_prompt(self) -> str:
        return (
            "Voce e um analista de futebol. Produza uma analise objetiva em "
            "portugues do Brasil. Diferencie fatos verificados, dados historicos "
            "do banco e inferencias. Nao invente lesoes, suspensoes, escalacoes "
            "ou noticias; quando a web nao confirmar um ponto, marque como "
            "incerteza. Use as probabilidades do modelo local como base, sem "
            "prometer resultado."
        )

    def _response_format_schema(self) -> Dict[str, Any]:
        source_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": ["string", "null"]},
                "url": {"type": ["string", "null"]},
                "source": {"type": ["string", "null"]},
            },
            "required": ["title", "url", "source"],
        }

        return {
            "type": "json_schema",
            "name": "football_match_ai_analysis",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "resumo": {"type": "string"},
                    "fatores_chave": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "forma_e_contexto": {"type": "string"},
                    "leitura_tatica": {"type": "string"},
                    "riscos_e_incertezas": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "recomendacao_modelo": {"type": "string"},
                    "fontes_consultadas": {
                        "type": "array",
                        "items": source_schema,
                    },
                },
                "required": [
                    "resumo",
                    "fatores_chave",
                    "forma_e_contexto",
                    "leitura_tatica",
                    "riscos_e_incertezas",
                    "recomendacao_modelo",
                    "fontes_consultadas",
                ],
            },
        }

    def _build_response(
        self,
        home_team: Team,
        away_team: Team,
        prediction: Dict[str, Any],
        local_context: Dict[str, Any],
        ai_status: str,
        analysis: Optional[Dict[str, Any]] = None,
        web_sources: Optional[List[Dict[str, Any]]] = None,
        ai_error: Optional[str] = None,
    ) -> Dict[str, Any]:
        if analysis is None:
            analysis = self._fallback_analysis(local_context, ai_error)

        return {
            "home_team": home_team.name,
            "away_team": away_team.name,
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "generated_at": datetime.datetime.utcnow(),
            "ai_status": ai_status,
            "ai_model": AI_ANALYSIS_MODEL if OPENAI_API_KEY else None,
            "ai_error": ai_error,
            "prediction": PredictionResponse(**prediction),
            "analysis": analysis,
            "local_context": local_context,
            "web_sources": web_sources or analysis.get("fontes_consultadas", []),
        }

    def _fallback_analysis(
        self,
        local_context: Dict[str, Any],
        ai_error: Optional[str],
    ) -> Dict[str, Any]:
        prediction = local_context["prediction"]
        home = local_context["teams"]["home"]["name"]
        away = local_context["teams"]["away"]["name"]
        home_stats = local_context["team_analytics"]["home"]
        away_stats = local_context["team_analytics"]["away"]
        head_to_head = local_context["head_to_head"]

        factors = [
            (
                f"Modelo local: {home} {prediction['home_win_probability']}%, "
                f"empate {prediction['draw_probability']}%, "
                f"{away} {prediction['away_win_probability']}%."
            ),
            (
                f"Gols esperados: {home} {prediction['predicted_home_goals']} x "
                f"{prediction['predicted_away_goals']} {away}."
            ),
            (
                f"Confronto direto no banco: {head_to_head['total_matches']} jogos, "
                f"{head_to_head['team1']['wins']} vitorias de {home}, "
                f"{head_to_head['team2']['wins']} de {away} e "
                f"{head_to_head['draws']} empates."
            ),
        ]

        if ai_error:
            factors.append(f"Enriquecimento por IA indisponivel: {ai_error}")

        return {
            "resumo": (
                f"Analise local para {home} x {away}. O placar mais provavel pelo "
                f"modelo e {prediction['most_likely_score']}, com confianca "
                f"{prediction['confidence']}%."
            ),
            "fatores_chave": factors,
            "forma_e_contexto": (
                f"Forma recente no banco: {home} {home_stats['recent_form'] or 'sem dados'}; "
                f"{away} {away_stats['recent_form'] or 'sem dados'}."
            ),
            "leitura_tatica": (
                "Sem consulta web ativa, a leitura tatica fica limitada ao historico "
                "de gols, resultados e estatisticas importadas."
            ),
            "riscos_e_incertezas": [
                "A base local pode nao refletir convocacoes, lesoes ou suspensoes recentes.",
                "Use o resultado como apoio analitico, nao como garantia de placar.",
            ],
            "recomendacao_modelo": (
                "Priorize a predição local quando a busca web estiver indisponivel; "
                "ative OPENAI_API_KEY para contexto recente."
            ),
            "fontes_consultadas": [],
        }

    def _extract_output_text(self, payload: Dict[str, Any]) -> Optional[str]:
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]

        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if isinstance(content.get("text"), str):
                    return content["text"]

        return None

    def _extract_openai_sources(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        sources: List[Dict[str, Any]] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                raw_sources = value.get("sources")
                if isinstance(raw_sources, list):
                    for source in raw_sources:
                        normalized = self._normalize_source(source)
                        if normalized:
                            sources.append(normalized)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(payload)
        return self._dedupe_sources(sources)

    def _merge_sources(
        self,
        model_sources: List[Dict[str, Any]],
        api_sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        normalized = []
        for source in [*model_sources, *api_sources]:
            item = self._normalize_source(source)
            if item:
                normalized.append(item)
        return self._dedupe_sources(normalized)

    def _normalize_source(self, source: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(source, dict):
            return None

        url = source.get("url") or source.get("uri") or source.get("link")
        title = source.get("title") or source.get("name")
        source_name = source.get("source") or source.get("domain")

        if not url and not title and not source_name:
            return None

        return {
            "title": title,
            "url": url,
            "source": source_name,
        }

    def _dedupe_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for source in sources:
            key = source.get("url") or source.get("title") or source.get("source")
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(source)
            if len(unique) >= 10:
                break
        return unique

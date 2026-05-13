"""
Cliente HTTP para acessar a API do SofaScore com bypass de WAF.
Usa curl_cffi com TLS fingerprinting para evitar bloqueios.
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from curl_cffi import requests as curl_requests
from app.config import (
    SOFASCORE_API_BASE_URL,
    SOFASCORE_RATE_LIMIT_DELAY,
    SOFASCORE_MAX_RETRIES,
    SOFASCORE_TIMEOUT,
)

logger = logging.getLogger(__name__)


class SofaScoreClient:
    """Cliente para SofaScore API com retry logic e rate limiting"""
    
    def __init__(self):
        self.base_url = SOFASCORE_API_BASE_URL
        self.rate_limit_delay = SOFASCORE_RATE_LIMIT_DELAY
        self.max_retries = SOFASCORE_MAX_RETRIES
        self.timeout = SOFASCORE_TIMEOUT
        self.last_request_time = 0
    
    def _apply_rate_limit(self):
        """Aplica delay entre requisições para evitar rate limit"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: aguardando {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Faz requisição com retry automático e rate limiting.
        
        Args:
            method: GET, POST, etc
            endpoint: ex "/event/12345"
            params: query parameters
            json_data: dados para POST
            retry_count: contador interno de tentativas
        
        Returns:
            Response JSON ou None se falhar
        """
        url = f"{self.base_url}{endpoint}"
        
        # Rate limiting
        self._apply_rate_limit()
        
        # Headers para fingerprinting
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0",
            "Referer": "https://www.sofascore.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        
        try:
            logger.debug(f"Requesting {method} {url}")
            
            response = curl_requests.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers,
                impersonate="chrome120",  # TLS fingerprinting
                timeout=self.timeout,
            )
            
            response.raise_for_status()
            return response.json()
            
        except curl_requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                logger.warning(f"WAF blocked request: {url}")
            elif response.status_code == 429:
                logger.warning(f"Rate limited. Waiting before retry...")
                if retry_count < self.max_retries:
                    time.sleep(5 * (retry_count + 1))  # Exponential backoff
                    return self._make_request(method, endpoint, params, json_data, retry_count + 1)
            elif response.status_code in [500, 502, 503]:
                logger.warning(f"Server error {response.status_code}. Retrying...")
                if retry_count < self.max_retries:
                    time.sleep(2 * (retry_count + 1))
                    return self._make_request(method, endpoint, params, json_data, retry_count + 1)
            
            logger.error(f"HTTP Error: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            if retry_count < self.max_retries:
                logger.info(f"Retrying... ({retry_count + 1}/{self.max_retries})")
                time.sleep(2 * (retry_count + 1))
                return self._make_request(method, endpoint, params, json_data, retry_count + 1)
            return None
    
    # ============ Tournament Endpoints ============
    
    def get_unique_tournaments(self) -> Optional[Dict[str, Any]]:
        """Obtém lista de todos os torneios (incluindo Copa e Eliminatórias)"""
        return self._make_request("GET", "/sport/football/unique-tournaments")
    
    def get_tournament(self, tournament_id: int) -> Optional[Dict[str, Any]]:
        """Obtém dados de um torneio específico"""
        return self._make_request("GET", f"/unique-tournament/{tournament_id}")
    
    def get_tournament_seasons(self, tournament_id: int) -> Optional[Dict[str, Any]]:
        """Obtém temporadas de um torneio"""
        return self._make_request("GET", f"/unique-tournament/{tournament_id}/seasons")
    
    def get_tournament_season_standings(
        self, 
        tournament_id: int, 
        season_id: int, 
        group_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Obtém standings (tabela) de um torneio"""
        endpoint = f"/unique-tournament/{tournament_id}/season/{season_id}/standings"
        params = {}
        if group_name:
            params["groupName"] = group_name
        return self._make_request("GET", endpoint, params=params)
    
    # ============ Match Endpoints ============
    
    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Obtém dados detalhados de uma partida"""
        return self._make_request("GET", f"/event/{event_id}")
    
    def get_event_statistics(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Obtém estatísticas de uma partida"""
        return self._make_request("GET", f"/event/{event_id}/statistics")
    
    def get_event_lineups(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Obtém escalações de uma partida"""
        return self._make_request("GET", f"/event/{event_id}/lineups")
    
    def get_event_incidents(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Obtém eventos da partida (gols, cartões, etc)"""
        return self._make_request("GET", f"/event/{event_id}/incidents")
    
    def get_scheduled_events(self, date: str) -> Optional[Dict[str, Any]]:
        """Obtém partidas agendadas para uma data (formato YYYY-MM-DD)"""
        return self._make_request("GET", f"/sport/football/scheduled-events/{date}")
    
    # ============ Team Endpoints ============
    
    def get_team(self, team_id: int) -> Optional[Dict[str, Any]]:
        """Obtém dados de um time"""
        return self._make_request("GET", f"/team/{team_id}")
    
    def get_team_players(self, team_id: int) -> Optional[Dict[str, Any]]:
        """Obtém elenco de um time"""
        return self._make_request("GET", f"/team/{team_id}/players")
    
    def get_team_tournaments(self, team_id: int) -> Optional[Dict[str, Any]]:
        """Obtém torneios que um time participa"""
        return self._make_request("GET", f"/team/{team_id}/tournaments")
    
    # ============ Player Endpoints ============
    
    def get_player(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Obtém dados de um jogador"""
        return self._make_request("GET", f"/player/{player_id}")
    
    def get_player_statistics(
        self, 
        player_id: int, 
        tournament_id: int, 
        season_id: int
    ) -> Optional[Dict[str, Any]]:
        """Obtém estatísticas de um jogador em um torneio"""
        return self._make_request(
            "GET", 
            f"/player/{player_id}/tournament/{tournament_id}/season/{season_id}/statistics"
        )
    
    # ============ Helper Methods ============
    
    def get_tournament_by_name(self, name: str) -> Optional[int]:
        """Encontra tournament_id pelo nome"""
        data = self.get_unique_tournaments()
        if not data or "tournaments" not in data:
            return None
        
        for tournament in data["tournaments"]:
            if tournament.get("name", "").lower() == name.lower():
                return tournament.get("id")
        
        return None
    
    def get_matches_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Obtém todas as partidas em um intervalo de datas"""
        matches = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            data = self.get_scheduled_events(date_str)
            
            if data and "events" in data:
                matches.extend(data["events"])
            
            current_date += timedelta(days=1)
        
        return matches

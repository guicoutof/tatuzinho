from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# ============ Tournament Schemas ============
class TournamentBase(BaseModel):
    name: str
    slug: str
    season: int
    type: str  # "worldcup", "qualifier"
    country: Optional[str] = None


class TournamentCreate(TournamentBase):
    source_id: str
    source: str = "sofascore"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class Tournament(TournamentBase):
    id: int
    source_id: str
    source: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Team Schemas ============
class TeamBase(BaseModel):
    name: str
    code: str
    country: str


class TeamCreate(TeamBase):
    source_id: int
    source: str = "sofascore"
    logo_url: Optional[str] = None


class TeamStats(BaseModel):
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int


class Team(TeamBase):
    id: int
    source_id: int
    source: str
    logo_url: Optional[str]
    stats: TeamStats

    class Config:
        from_attributes = True


class TeamWithPlayers(Team):
    players: List["Player"] = []


# ============ Player Schemas ============
class PlayerBase(BaseModel):
    name: str
    position: str


class PlayerCreate(PlayerBase):
    source_id: int
    source: str = "sofascore"
    number: Optional[int] = None
    birth_date: Optional[datetime] = None
    nationality: Optional[str] = None
    height: Optional[int] = None
    team_id: Optional[int] = None


class PlayerStats(BaseModel):
    matches_played: int
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int


class Player(PlayerBase):
    id: int
    source_id: int
    source: str
    number: Optional[int]
    nationality: Optional[str]
    height: Optional[int]
    stats: PlayerStats

    class Config:
        from_attributes = True


# ============ Match Schemas ============
class MatchBase(BaseModel):
    match_date: datetime
    status: str
    phase: Optional[str] = None
    group: Optional[str] = None


class MatchCreate(MatchBase):
    source_id: int
    source: str = "sofascore"
    tournament_id: int
    home_team_id: int
    away_team_id: int
    venue: Optional[str] = None
    city: Optional[str] = None


class MatchResult(BaseModel):
    home_score: Optional[int]
    away_score: Optional[int]
    home_score_ht: Optional[int]
    away_score_ht: Optional[int]
    attendance: Optional[int] = None


class Match(MatchBase):
    id: int
    source_id: int
    source: str
    tournament_id: int
    home_team_id: int
    away_team_id: int
    result: MatchResult
    venue: Optional[str]
    city: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MatchWithDetails(Match):
    home_team: Team
    away_team: Team
    tournament: Tournament


# ============ Match Statistics Schemas ============
class MatchStatisticBase(BaseModel):
    possession: Optional[float] = None
    shots: int
    shots_on_target: int
    passes: int
    pass_accuracy: Optional[float] = None


class MatchStatisticCreate(MatchStatisticBase):
    match_id: int
    player_id: Optional[int] = None
    team_id: Optional[int] = None
    tackles: int = 0
    interceptions: int = 0
    fouls: int = 0
    offsides: int = 0
    corners: int = 0


class MatchStatistic(MatchStatisticBase):
    id: int
    match_id: int
    player_id: Optional[int]
    team_id: Optional[int]
    tackles: int
    interceptions: int
    fouls: int
    offsides: int
    corners: int
    rating: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Prediction Schemas ============
class PredictionBase(BaseModel):
    home_win_probability: float = Field(..., ge=0.0, le=1.0)
    draw_probability: float = Field(..., ge=0.0, le=1.0)
    away_win_probability: float = Field(..., ge=0.0, le=1.0)


class PredictionCreate(PredictionBase):
    match_id: int
    predicted_home_score: Optional[float] = None
    predicted_away_score: Optional[float] = None
    over_25_probability: Optional[float] = None
    model_version: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class Prediction(PredictionBase):
    id: int
    match_id: int
    predicted_home_score: Optional[float]
    predicted_away_score: Optional[float]
    over_25_probability: Optional[float]
    model_version: str
    confidence: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PredictionWithMatch(Prediction):
    match: MatchWithDetails


# ============ Prediction Schemas (Response) ============
class PredictionResponse(BaseModel):
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    most_likely_score: str
    predicted_home_goals: float
    predicted_away_goals: float
    confidence: float


# ============ Analytics Schemas (Response) ============
class TeamAnalytics(BaseModel):
    team: Team
    recent_form: List[str]  # List of W/D/L
    win_rate: float
    average_goals_for: float
    average_goals_against: float
    average_possession: Optional[float]
    top_scorers: List[Player] = []


class TournamentStanding(BaseModel):
    position: int
    team: Team
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int


class TopScorersResponse(BaseModel):
    tournament_id: int
    scorers: List[Player]


# Update forward references
TeamWithPlayers.model_rebuild()
PredictionWithMatch.model_rebuild()
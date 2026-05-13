"""
SQLAlchemy ORM models for Tatuzinho application.

Defines database schema for tournaments, teams, players, matches, and related
entities. All models use proper indexing, relationships with cascade rules,
and timestamps for auditing.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    ForeignKey, Index, UniqueConstraint, Table
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Tournament(Base):
    """Tournament entity representing World Cup, Qualifiers, etc.
    
    Each tournament has multiple matches and teams participating. Tournaments
    are uniquely identified by their SofaScore ID to prevent duplicates during
    data synchronization from the external API.
    
    Attributes:
        id: Primary key (auto-generated).
        sofascore_id: External ID from SofaScore API (unique).
        name: Full tournament name (e.g., "FIFA World Cup 2026").
        slug: URL-friendly identifier (e.g., "world-cup-2026").
        season: Year/season of tournament (e.g., 2026).
        type: Tournament type ("worldcup", "qualifier", etc.).
        country: Country if tournament is a qualifier.
        start_date: Tournament start date (optional).
        end_date: Tournament end date (optional).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    sofascore_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    season = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    country = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    matches = relationship(
        "Match",
        back_populates="tournament",
        cascade="all, delete-orphan",
    )
    teams = relationship(
        "Team",
        secondary="tournament_teams",
        back_populates="tournaments",
    )

    __table_args__ = (
        Index("idx_tournament_sofascore_id", sofascore_id),
        Index("idx_tournament_season", season),
    )


class Team(Base):
    """National team entity representing countries in tournaments.
    
    Teams participate in matches and tournaments. Each team has a unique
    SofaScore ID and ISO3 country code. Aggregate statistics are maintained
    for performance optimization.
    
    Attributes:
        id: Primary key (auto-generated).
        sofascore_id: External ID from SofaScore API (unique).
        name: Team name (e.g., "Brazil").
        code: ISO3 country code (e.g., "BRA").
        country: Full country name.
        logo_url: URL to team flag/logo image.
        matches_played: Total matches played (aggregate).
        wins: Total matches won (aggregate).
        draws: Total matches drawn (aggregate).
        losses: Total matches lost (aggregate).
        goals_for: Total goals scored (aggregate).
        goals_against: Total goals conceded (aggregate).
        goal_difference: Goals for minus goals against (aggregate).
        points: Total points (aggregate, 3 per win + 1 per draw).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    sofascore_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    code = Column(String(3), unique=True, nullable=False)
    country = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    
    # Aggregate statistics
    matches_played = Column(Integer, default=0, nullable=False)
    wins = Column(Integer, default=0, nullable=False)
    draws = Column(Integer, default=0, nullable=False)
    losses = Column(Integer, default=0, nullable=False)
    goals_for = Column(Integer, default=0, nullable=False)
    goals_against = Column(Integer, default=0, nullable=False)
    goal_difference = Column(Integer, default=0, nullable=False)
    points = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    players = relationship(
        "Player",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    home_matches = relationship(
        "Match",
        foreign_keys="Match.home_team_id",
        back_populates="home_team",
    )
    away_matches = relationship(
        "Match",
        foreign_keys="Match.away_team_id",
        back_populates="away_team",
    )
    tournaments = relationship(
        "Tournament",
        secondary="tournament_teams",
        back_populates="teams",
    )

    __table_args__ = (
        Index("idx_team_sofascore_id", sofascore_id),
        Index("idx_team_code", code),
    )


class Player(Base):
    """Player entity representing individual athletes.
    
    Each player belongs to a team and participates in matches. Player statistics
    are maintained for career tracking and analytics.
    
    Attributes:
        id: Primary key (auto-generated).
        sofascore_id: External ID from SofaScore API (unique).
        name: Player full name.
        position: Playing position (GK, DEF, MID, FWD).
        number: Shirt number (nullable if not assigned).
        birth_date: Player date of birth (optional).
        nationality: Player nationality (optional).
        height: Player height in centimeters (optional).
        team_id: Foreign key to Team.
        matches_played: Career matches played (aggregate).
        goals: Career goals scored (aggregate).
        assists: Career assists (aggregate).
        yellow_cards: Career yellow cards (aggregate).
        red_cards: Career red cards (aggregate).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    sofascore_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    position = Column(String, nullable=False)
    number = Column(Integer, nullable=True)
    birth_date = Column(DateTime, nullable=True)
    nationality = Column(String, nullable=True)
    height = Column(Integer, nullable=True)
    
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    
    # Career statistics
    matches_played = Column(Integer, default=0, nullable=False)
    goals = Column(Integer, default=0, nullable=False)
    assists = Column(Integer, default=0, nullable=False)
    yellow_cards = Column(Integer, default=0, nullable=False)
    red_cards = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    team = relationship("Team", back_populates="players")
    match_stats = relationship(
        "MatchStatistic",
        back_populates="player",
    )

    __table_args__ = (
        Index("idx_player_sofascore_id", sofascore_id),
        Index("idx_player_team_id", team_id),
    )


class Match(Base):
    """Partidas"""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    sofascore_id = Column(Integer, unique=True, index=True)
    
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    
    match_date = Column(DateTime, index=True)
    status = Column(String)  # "scheduled", "inprogress", "finished", "cancelled"
    
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    home_score_ht = Column(Integer, nullable=True)  # Half-time
    away_score_ht = Column(Integer, nullable=True)
    
    group = Column(String, nullable=True)  # A, B, C, etc (para fase de grupos)
    phase = Column(String, nullable=True)  # "group", "round_of_16", "quarter", "semi", "final"
    
    venue = Column(String, nullable=True)
    city = Column(String, nullable=True)
    attendance = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tournament = relationship("Tournament", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    statistics = relationship("MatchStatistic", back_populates="match", cascade="all, delete-orphan")
    predictions = relationship("PredictionCache", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_match_sofascore_id", sofascore_id),
        Index("idx_match_date", match_date),
        Index("idx_match_tournament", tournament_id),
        Index("idx_match_status", status),
        UniqueConstraint("sofascore_id", name="uq_match_sofascore_id"),
    )


class MatchStatistic(Base):
    """Estatísticas por partida (times e jogadores)"""
    __tablename__ = "match_statistics"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)  # Stats agregados do time
    
    # Estatísticas gerais
    possession = Column(Float, nullable=True)  # %
    shots = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    passes = Column(Integer, default=0)
    pass_accuracy = Column(Float, nullable=True)  # %
    tackles = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    fouls = Column(Integer, default=0)
    offsides = Column(Integer, default=0)
    corners = Column(Integer, default=0)
    throw_ins = Column(Integer, default=0)
    crosses = Column(Integer, default=0)
    cross_accuracy = Column(Float, nullable=True)  # %
    aerials = Column(Integer, default=0)
    aerial_won = Column(Integer, default=0)
    
    # Estatísticas de jogador
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    minutes_played = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)  # SofaScore rating
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    match = relationship("Match", back_populates="statistics")
    player = relationship("Player", back_populates="match_stats")
    team = relationship("Team")

    __table_args__ = (
        Index("idx_match_stat_match_id", match_id),
        Index("idx_match_stat_player_id", player_id),
        Index("idx_match_stat_team_id", team_id),
    )


class PredictionCache(Base):
    """Cache de previsões calculadas"""
    __tablename__ = "prediction_cache"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), unique=True, index=True)
    
    home_win_probability = Column(Float)  # 0.0 - 1.0
    draw_probability = Column(Float)
    away_win_probability = Column(Float)
    
    predicted_home_score = Column(Float, nullable=True)
    predicted_away_score = Column(Float, nullable=True)
    over_25_probability = Column(Float, nullable=True)  # Over 2.5 goals
    
    model_version = Column(String)  # Versão do modelo usado
    confidence = Column(Float)  # 0.0 - 1.0, baseado em dados históricos
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    match = relationship("Match", back_populates="predictions")

    __table_args__ = (
        Index("idx_pred_match_id", match_id),
        Index("idx_pred_created_at", created_at),
    )


# Tabela associativa para relação M2M Tournament-Team
tournament_teams = Table(
    "tournament_teams",
    Base.metadata,
    Column("tournament_id", Integer, ForeignKey("tournaments.id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("teams.id"), primary_key=True),
)
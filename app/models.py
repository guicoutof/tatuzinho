from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    ForeignKey, Index, UniqueConstraint, Table
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Tournament(Base):
    """Torneios (Copa do Mundo, Eliminatórias)"""
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    sofascore_id = Column(Integer, unique=True, index=True)  # ID externo SofaScore
    name = Column(String, index=True)  # ex: "FIFA World Cup 2026"
    slug = Column(String, unique=True)  # ex: "world-cup-2026"
    season = Column(Integer)  # 2026, 2025, etc
    type = Column(String)  # "worldcup", "qualifier", etc
    country = Column(String, nullable=True)  # Pais se for qualificatoria
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    matches = relationship("Match", back_populates="tournament", cascade="all, delete-orphan")
    teams = relationship("Team", secondary="tournament_teams", back_populates="tournaments")

    __table_args__ = (
        Index("idx_tournament_sofascore_id", sofascore_id),
        Index("idx_tournament_season", season),
    )


class Team(Base):
    """Seleções Nacionais"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    sofascore_id = Column(Integer, unique=True, index=True)
    name = Column(String, index=True)  # ex: "Brazil"
    code = Column(String(3), unique=True)  # ex: "BRA"
    country = Column(String)
    logo_url = Column(String, nullable=True)
    
    # Estatísticas agregadas
    matches_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    goal_difference = Column(Integer, default=0)
    points = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    players = relationship("Player", back_populates="team", cascade="all, delete-orphan")
    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")
    tournaments = relationship("Tournament", secondary="tournament_teams", back_populates="teams")

    __table_args__ = (
        Index("idx_team_sofascore_id", sofascore_id),
        Index("idx_team_code", code),
    )


class Player(Base):
    """Jogadores"""
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    sofascore_id = Column(Integer, unique=True, index=True)
    name = Column(String, index=True)
    position = Column(String)  # GK, DEF, MID, FWD
    number = Column(Integer, nullable=True)
    birth_date = Column(DateTime, nullable=True)
    nationality = Column(String, nullable=True)
    height = Column(Integer, nullable=True)  # cm
    
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    
    # Estatísticas de carreira
    matches_played = Column(Integer, default=0)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="players")
    match_stats = relationship("MatchStatistic", back_populates="player")

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
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    ForeignKey, Index, UniqueConstraint, Table
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, index=True, nullable=False)
    source = Column(String, nullable=False, default="statsbomb")
    name = Column(String, index=True, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    season = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    country = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
        Index("idx_tournament_source", source_id, source),
        Index("idx_tournament_season", season),
        UniqueConstraint("source_id", "source", name="uq_tournament_source"),
    )


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, index=True, nullable=False)
    source = Column(String, nullable=False, default="statsbomb")
    name = Column(String, index=True, nullable=False)
    code = Column(String(3), nullable=False)
    country = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)

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
        Index("idx_team_source", source_id, source),
        Index("idx_team_code", code),
        UniqueConstraint("source_id", "source", name="uq_team_source"),
    )


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, index=True, nullable=False)
    source = Column(String, nullable=False, default="statsbomb")
    name = Column(String, index=True, nullable=False)
    position = Column(String, nullable=False)
    number = Column(Integer, nullable=True)
    birth_date = Column(DateTime, nullable=True)
    nationality = Column(String, nullable=True)
    height = Column(Integer, nullable=True)

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    matches_played = Column(Integer, default=0, nullable=False)
    goals = Column(Integer, default=0, nullable=False)
    assists = Column(Integer, default=0, nullable=False)
    yellow_cards = Column(Integer, default=0, nullable=False)
    red_cards = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    team = relationship("Team", back_populates="players")
    match_stats = relationship(
        "MatchStatistic",
        back_populates="player",
    )

    __table_args__ = (
        Index("idx_player_source", source_id, source),
        Index("idx_player_team_id", team_id),
        UniqueConstraint("source_id", "source", name="uq_player_source"),
    )


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, index=True, nullable=False)
    source = Column(String, nullable=False, default="statsbomb")

    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))

    match_date = Column(DateTime, index=True)
    status = Column(String)

    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    home_score_ht = Column(Integer, nullable=True)
    away_score_ht = Column(Integer, nullable=True)

    group = Column(String, nullable=True)
    phase = Column(String, nullable=True)

    venue = Column(String, nullable=True)
    city = Column(String, nullable=True)
    attendance = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tournament = relationship("Tournament", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    statistics = relationship("MatchStatistic", back_populates="match", cascade="all, delete-orphan")
    predictions = relationship("PredictionCache", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_match_source", source_id, source),
        Index("idx_match_date", match_date),
        Index("idx_match_tournament", tournament_id),
        Index("idx_match_status", status),
        UniqueConstraint("source_id", "source", name="uq_match_source"),
    )


class MatchStatistic(Base):
    __tablename__ = "match_statistics"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    possession = Column(Float, nullable=True)
    shots = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    passes = Column(Integer, default=0)
    pass_accuracy = Column(Float, nullable=True)
    tackles = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    fouls = Column(Integer, default=0)
    offsides = Column(Integer, default=0)
    corners = Column(Integer, default=0)
    throw_ins = Column(Integer, default=0)
    crosses = Column(Integer, default=0)
    cross_accuracy = Column(Float, nullable=True)
    aerials = Column(Integer, default=0)
    aerial_won = Column(Integer, default=0)

    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    minutes_played = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="statistics")
    player = relationship("Player", back_populates="match_stats")
    team = relationship("Team")

    __table_args__ = (
        Index("idx_match_stat_match_id", match_id),
        Index("idx_match_stat_player_id", player_id),
        Index("idx_match_stat_team_id", team_id),
    )


class PredictionCache(Base):
    __tablename__ = "prediction_cache"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), unique=True, index=True)

    home_win_probability = Column(Float)
    draw_probability = Column(Float)
    away_win_probability = Column(Float)

    predicted_home_score = Column(Float, nullable=True)
    predicted_away_score = Column(Float, nullable=True)
    over_25_probability = Column(Float, nullable=True)

    model_version = Column(String)
    confidence = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    match = relationship("Match", back_populates="predictions")

    __table_args__ = (
        Index("idx_pred_match_id", match_id),
        Index("idx_pred_created_at", created_at),
    )


tournament_teams = Table(
    "tournament_teams",
    Base.metadata,
    Column("tournament_id", Integer, ForeignKey("tournaments.id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("teams.id"), primary_key=True),
)

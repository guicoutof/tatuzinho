"""
Custom exception classes for Tatuzinho project.

This module defines domain-specific exceptions that are raised for business logic
errors. All exceptions inherit from TatuzinhoException for consistent handling
in middleware and routers.
"""

from typing import Optional


class TatuzinhoException(Exception):
    """Base exception for all Tatuzinho errors.
    
    All domain-specific exceptions should inherit from this class to enable
    consistent error handling across the application.
    """
    pass


class TournamentNotFound(TatuzinhoException):
    """Raised when a tournament is not found in the database.
    
    Args:
        tournament_id: ID of the tournament that was not found.
    """
    def __init__(self, tournament_id: int) -> None:
        self.tournament_id = tournament_id
        super().__init__(f"Tournament with ID {tournament_id} not found")


class TeamNotFound(TatuzinhoException):
    """Raised when a team is not found in the database.
    
    Args:
        team_id: ID of the team that was not found.
    """
    def __init__(self, team_id: int) -> None:
        self.team_id = team_id
        super().__init__(f"Team with ID {team_id} not found")


class PlayerNotFound(TatuzinhoException):
    """Raised when a player is not found in the database.
    
    Args:
        player_id: ID of the player that was not found.
    """
    def __init__(self, player_id: int) -> None:
        self.player_id = player_id
        super().__init__(f"Player with ID {player_id} not found")


class MatchNotFound(TatuzinhoException):
    """Raised when a match is not found in the database.
    
    Args:
        match_id: ID of the match that was not found.
    """
    def __init__(self, match_id: int) -> None:
        self.match_id = match_id
        super().__init__(f"Match with ID {match_id} not found")


class DataParsingError(TatuzinhoException):
    """Raised when external API data cannot be parsed or validated.
    
    Args:
        api_name: Name of the API that failed (e.g., 'SofaScore').
        message: Detailed error message about what failed.
    """
    def __init__(self, api_name: str, message: str) -> None:
        self.api_name = api_name
        self.error_message = message
        super().__init__(f"Failed to parse {api_name} data: {message}")


class SofaScoreAPIError(TatuzinhoException):
    """Raised when SofaScore API calls fail after retries.
    
    Args:
        endpoint: The API endpoint that failed (e.g., '/tournament/1234').
        status_code: HTTP status code returned by the API.
        retry_count: Number of retries attempted before giving up.
    """
    def __init__(
        self,
        endpoint: str,
        status_code: int,
        retry_count: int,
    ) -> None:
        self.endpoint = endpoint
        self.status_code = status_code
        self.retry_count = retry_count
        super().__init__(
            f"SofaScore API failed for {endpoint} after {retry_count} retries "
            f"(status: {status_code})"
        )


class DatabaseError(TatuzinhoException):
    """Raised for database operation failures.
    
    Args:
        operation: Description of the operation that failed (e.g., 'insert tournament').
        message: Detailed error message.
    """
    def __init__(self, operation: str, message: str) -> None:
        self.operation = operation
        self.error_message = message
        super().__init__(f"Database error during {operation}: {message}")


class DuplicateEntityError(TatuzinhoException):
    """Raised when attempting to create an entity that already exists.
    
    Args:
        entity_type: Type of entity (e.g., 'Tournament', 'Team').
        identifier: Unique identifier that caused the conflict (e.g., 'name' or 'source_id').
        value: Value of the identifier.
    """
    def __init__(
        self,
        entity_type: str,
        identifier: str,
        value: str,
    ) -> None:
        self.entity_type = entity_type
        self.identifier = identifier
        self.value = value
        super().__init__(
            f"{entity_type} with {identifier}='{value}' already exists"
        )


class ValidationError(TatuzinhoException):
    """Raised when input validation fails.
    
    Args:
        field: Name of the field that failed validation.
        message: Detailed validation error message.
    """
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.error_message = message
        super().__init__(f"Validation error for field '{field}': {message}")


class InvalidOperationError(TatuzinhoException):
    """Raised when an operation cannot be performed in the current state.
    
    Args:
        message: Detailed message about why the operation is invalid.
    """
    def __init__(self, message: str) -> None:
        super().__init__(message)

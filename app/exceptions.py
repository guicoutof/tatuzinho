from typing import Optional


class TatuzinhoException(Exception):
    pass


class TournamentNotFound(TatuzinhoException):
    def __init__(self, tournament_id: int) -> None:
        self.tournament_id = tournament_id
        super().__init__(f"Tournament with ID {tournament_id} not found")


class TeamNotFound(TatuzinhoException):
    def __init__(self, team_id: int) -> None:
        self.team_id = team_id
        super().__init__(f"Team with ID {team_id} not found")


class PlayerNotFound(TatuzinhoException):
    def __init__(self, player_id: int) -> None:
        self.player_id = player_id
        super().__init__(f"Player with ID {player_id} not found")


class MatchNotFound(TatuzinhoException):
    def __init__(self, match_id: int) -> None:
        self.match_id = match_id
        super().__init__(f"Match with ID {match_id} not found")


class DataParsingError(TatuzinhoException):
    def __init__(self, api_name: str, message: str) -> None:
        self.api_name = api_name
        self.error_message = message
        super().__init__(f"Failed to parse {api_name} data: {message}")


class DatabaseError(TatuzinhoException):
    def __init__(self, operation: str, message: str) -> None:
        self.operation = operation
        self.error_message = message
        super().__init__(f"Database error during {operation}: {message}")


class DuplicateEntityError(TatuzinhoException):
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
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.error_message = message
        super().__init__(f"Validation error for field '{field}': {message}")


class InvalidOperationError(TatuzinhoException):
    def __init__(self, message: str) -> None:
        super().__init__(message)

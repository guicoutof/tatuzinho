"""
Base repository class for all data access operations.

This module provides the abstract BaseRepository class that all concrete
repositories inherit from. It defines the common CRUD interface and ensures
consistent error handling and logging across all data access layers.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.config import logger
from app.exceptions import DatabaseError

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base class for all repository implementations.
    
    Provides common CRUD operations and ensures consistent error handling
    and logging across all concrete repositories.
    
    Type Parameters:
        T: The model type this repository manages.
    
    Attributes:
        db: SQLAlchemy database session.
        model_name: Name of the model for logging purposes.
    """
    
    def __init__(self, db: Session, model_name: str):
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session.
            model_name: Name of the model (e.g., "Tournament", "Team") for logging.
        
        Raises:
            ValueError: If db session is None.
        """
        if not db:
            raise ValueError("Database session cannot be None")
        
        self.db = db
        self.model_name = model_name
        logger.debug(f"Initialized {self.__class__.__name__} for {model_name}")
    
    @abstractmethod
    def find_by_id(self, entity_id: int) -> Optional[T]:
        """Find entity by primary key.
        
        Args:
            entity_id: Primary key value.
        
        Returns:
            Entity if found, None otherwise.
        
        Raises:
            DatabaseError: If query execution fails.
        """
        pass
    
    @abstractmethod
    def find_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Find all entities with pagination.
        
        Args:
            skip: Number of records to skip (default: 0).
            limit: Maximum number of records (default: 100).
        
        Returns:
            List of entities matching criteria.
        
        Raises:
            DatabaseError: If query execution fails.
        """
        pass
    
    @abstractmethod
    def create(self, obj_in: Dict[str, Any]) -> T:
        """Create a new entity.
        
        Args:
            obj_in: Dictionary with entity data.
        
        Returns:
            Newly created entity.
        
        Raises:
            DatabaseError: If creation fails.
        """
        pass
    
    @abstractmethod
    def update(self, entity_id: int, obj_in: Dict[str, Any]) -> Optional[T]:
        """Update an existing entity.
        
        Args:
            entity_id: Primary key of entity to update.
            obj_in: Dictionary with updated data.
        
        Returns:
            Updated entity if found, None otherwise.
        
        Raises:
            DatabaseError: If update fails.
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete an entity.
        
        Args:
            entity_id: Primary key of entity to delete.
        
        Returns:
            True if deleted, False if not found.
        
        Raises:
            DatabaseError: If deletion fails.
        """
        pass
    
    def commit(self) -> None:
        """Commit current transaction.
        
        Raises:
            DatabaseError: If commit fails.
        """
        try:
            self.db.commit()
            logger.debug(f"Transaction committed for {self.model_name}")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to commit transaction: {e}")
            raise DatabaseError(f"Failed to commit changes for {self.model_name}") from e
    
    def rollback(self) -> None:
        """Rollback current transaction.
        
        Raises:
            DatabaseError: If rollback fails.
        """
        try:
            self.db.rollback()
            logger.debug(f"Transaction rolled back for {self.model_name}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to rollback transaction: {e}")
            raise DatabaseError(f"Failed to rollback changes for {self.model_name}") from e
    
    def refresh(self, obj: T) -> T:
        """Refresh entity from database to get latest state.
        
        Args:
            obj: Entity to refresh.
        
        Returns:
            Refreshed entity.
        
        Raises:
            DatabaseError: If refresh fails.
        """
        try:
            self.db.refresh(obj)
            return obj
        except SQLAlchemyError as e:
            logger.error(f"Failed to refresh {self.model_name}: {e}")
            raise DatabaseError(f"Failed to refresh {self.model_name}") from e
    
    def _handle_db_error(self, operation: str, error: Exception) -> None:
        """Handle database errors with consistent logging.
        
        Args:
            operation: Name of the operation that failed (e.g., "create", "update").
            error: The original exception.
        
        Raises:
            DatabaseError: Wraps the original error with context.
        """
        logger.error(
            f"Database error during {operation} for {self.model_name}",
            extra={
                "operation": operation,
                "model": self.model_name,
                "error": str(error),
            },
        )
        raise DatabaseError(
            f"Failed to {operation} {self.model_name}: {str(error)}"
        ) from error

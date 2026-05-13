"""
Base service class for all business logic services.

Services contain application business logic and orchestrate between routers and
repositories. They handle data validation, business rule enforcement, and
orchestration of complex operations.
"""

from typing import Optional, TypeVar, Generic
from sqlalchemy.orm import Session
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseService(ABC):
    """Abstract base class for all service classes.
    
    Provides common patterns and utilities for implementing business logic.
    All services should inherit from this class and implement CRUD operations
    as needed.
    
    Args:
        db: SQLAlchemy database session for persistence operations.
    """
    
    def __init__(self, db: Session) -> None:
        """Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session.
        """
        self.db = db
        self.logger = logger
    
    def commit(self) -> None:
        """Commit current database transaction.
        
        Raises:
            DatabaseError: If commit fails.
        """
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.logger.error(
                f"Transaction commit failed",
                extra={"error": str(e)},
            )
            raise
    
    def rollback(self) -> None:
        """Rollback current database transaction.
        
        Use when an error occurs and you need to undo pending changes.
        """
        try:
            self.db.rollback()
            self.logger.debug("Transaction rolled back")
        except Exception as e:
            self.logger.error(
                f"Transaction rollback failed",
                extra={"error": str(e)},
            )
    
    def refresh(self, obj: T) -> T:
        """Refresh object from database to get latest data.
        
        Args:
            obj: SQLAlchemy model instance to refresh.
        
        Returns:
            Refreshed object instance.
        """
        try:
            self.db.refresh(obj)
            return obj
        except Exception as e:
            self.logger.error(
                f"Failed to refresh object",
                extra={"error": str(e)},
            )
            raise

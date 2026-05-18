from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import Match as MatchSchema, MatchWithDetails
from app.services.match_service import MatchService
from app.exceptions import MatchNotFound, DatabaseError
from app.config import logger

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


def get_match_service(db: Session = Depends(get_db)) -> MatchService:
    return MatchService(db)


@router.get("/", response_model=List[MatchSchema], status_code=status.HTTP_200_OK)
async def list_matches(
    tournament_id: Optional[int] = Query(None),
    phase: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
    match_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    service: MatchService = Depends(get_match_service),
) -> List[MatchSchema]:
    try:
        return service.list_with_filters(
            tournament_id=tournament_id,
            phase=phase,
            group=group,
            status=match_status,
            skip=skip,
            limit=limit,
        )
    except DatabaseError as e:
        logger.error(f"Failed to list matches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch matches",
        )


@router.get("/{match_id}", response_model=MatchWithDetails, status_code=status.HTTP_200_OK)
async def get_match(
    match_id: int,
    service: MatchService = Depends(get_match_service),
) -> MatchWithDetails:
    try:
        return service.get_by_id(match_id)
    except MatchNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to fetch match: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch match",
        )


@router.get("/{match_id}/statistics", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_match_statistics(
    match_id: int,
    service: MatchService = Depends(get_match_service),
) -> Dict[str, Any]:
    try:
        return service.get_statistics(match_id)
    except MatchNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Failed to fetch match statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch match statistics",
        )

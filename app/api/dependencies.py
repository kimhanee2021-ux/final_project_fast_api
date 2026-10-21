from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.infrastructure.mysql_repositories import (
    MysqlGameCatalogRepository,
    MysqlLibraryRepository,
    MysqlUserRepository,
)
from app.services.recommendation_service import RecommendationService


def get_recommendation_service(
    request: Request, session: Session = Depends(get_session)
) -> RecommendationService:
    return RecommendationService(
        recommender=request.app.state.recommender,
        users=MysqlUserRepository(session),
        library=MysqlLibraryRepository(session),
        catalog=MysqlGameCatalogRepository(session),
    )

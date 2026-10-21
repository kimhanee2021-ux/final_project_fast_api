from fastapi import APIRouter, Depends, Query

from app.api.auth import get_current_user_id
from app.api.dependencies import get_recommendation_service
from app.core.config import DEFAULT_RECOMMENDATIONS, MAX_RECOMMENDATIONS
from app.schemas.recommendation import ErrorResponse, RecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/users/me/recommendations", tags=["recommendations"])


@router.get(
    "",
    response_model=RecommendationResponse,
    summary="로그인한 사용자의 보유 게임 기반 추천 조회",
    responses={
        401: {"model": ErrorResponse, "description": "토큰이 없거나 유효하지 않음 (UNAUTHENTICATED)"},
        404: {"model": ErrorResponse, "description": "토큰은 유효하나 회원이 없음 (USER_NOT_FOUND)"},
        409: {"model": ErrorResponse, "description": "추천에 쓸 수 있는 플레이한 게임이 없음 (NO_PLAYED_GAMES)"},
    },
)
def list_my_recommendations(
    limit: int = Query(DEFAULT_RECOMMENDATIONS, ge=1, le=MAX_RECOMMENDATIONS),
    user_id: int = Depends(get_current_user_id),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    return RecommendationResponse.from_result(service.recommend_for_user(user_id, limit))

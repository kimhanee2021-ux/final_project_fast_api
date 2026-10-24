from fastapi import APIRouter, Depends

from app.api.dependencies import get_recommender
from app.domain.recommender import Recommender
from app.schemas.recommendation import ErrorResponse, RecommendRequest, RecommendResponse

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post(
    "",
    response_model=RecommendResponse,
    summary="플레이 이력으로 게임 추천 (내부 API)",
    responses={
        422: {"model": ErrorResponse, "description": "모델이 아는 게임이 이력에 없음 (NO_KNOWN_GAMES)"},
    },
)
def recommend(body: RecommendRequest, recommender: Recommender = Depends(get_recommender)) -> RecommendResponse:
    result = recommender.recommend(
        [g.to_domain() for g in body.played_games], set(body.exclude_app_ids), body.limit, body.new_slots
    )
    return RecommendResponse.from_result(result)

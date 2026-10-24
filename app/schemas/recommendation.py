from pydantic import BaseModel, Field

from app.core.config import DEFAULT_RECOMMENDATIONS, MAX_HISTORY, MAX_RECOMMENDATIONS
from app.domain.recommender import OwnedGame, Recommendation, RecommendationResult


class PlayedGameIn(BaseModel):
    app_id: int
    playtime_hours: float = Field(ge=0)

    def to_domain(self) -> OwnedGame:
        return OwnedGame(self.app_id, self.playtime_hours)


class RecommendRequest(BaseModel):
    played_games: list[PlayedGameIn] = Field(
        max_length=MAX_HISTORY, description="플레이한 게임. 오래된 순 → 최근 순 (모델은 최근 이력부터 사용)"
    )
    exclude_app_ids: list[int] = Field(
        default_factory=list, max_length=MAX_HISTORY, description="추천에서 뺄 게임. 보유 게임 전체를 넘긴다"
    )
    limit: int = Field(DEFAULT_RECOMMENDATIONS, ge=1, le=MAX_RECOMMENDATIONS)
    new_slots: int = Field(0, ge=0, le=MAX_RECOMMENDATIONS, description="limit 중 신작(학습에 없던 게임) 칸 수")


class RecommendationOut(BaseModel):
    app_id: int
    score: float = Field(description="요청 내 순위용 점수 (확률/일치율 아님)")
    source: str = Field(description="main = 기본 추천, new = 학습에 없던 게임(신작) 칸")

    @classmethod
    def from_domain(cls, item: Recommendation) -> "RecommendationOut":
        return cls(app_id=item.app_id, score=round(item.score, 4), source=item.source)


class RecommendResponse(BaseModel):
    items: list[RecommendationOut] = Field(description="점수가 높은 순")
    used_app_ids: list[int] = Field(description="취향 계산에 실제 사용된 게임")
    ignored_app_ids: list[int] = Field(description="모델이 몰라서 취향 계산에서 빠진 게임")

    @classmethod
    def from_result(cls, result: RecommendationResult) -> "RecommendResponse":
        return cls(
            items=[RecommendationOut.from_domain(i) for i in result.items],
            used_app_ids=result.used_app_ids,
            ignored_app_ids=result.ignored_app_ids,
        )


class ErrorResponse(BaseModel):
    """code는 분기용 식별자, error는 사람이 읽는 문구."""

    code: str
    error: str

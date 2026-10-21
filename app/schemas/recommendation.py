from pydantic import BaseModel, Field

from app.services.recommendation_service import RecommendedGameDetail, UserRecommendations


class GameOut(BaseModel):
    name: str
    genre: str | None
    thumbnail_url: str | None


class RecommendedGame(BaseModel):
    rank: int
    app_id: int
    score: float = Field(description="요청 내 순위용 점수 (확률/일치율 아님)")
    source: str = Field(description="main = 기본 추천, new = 학습에 없던 게임(신작) 칸")
    game: GameOut | None = Field(description="games 카탈로그에 없는 게임이면 null")

    @classmethod
    def from_detail(cls, detail: RecommendedGameDetail) -> "RecommendedGame":
        game = detail.game
        return cls(
            rank=detail.rank,
            app_id=detail.recommendation.app_id,
            score=round(detail.recommendation.score, 4),
            source=detail.recommendation.source,
            game=GameOut(name=game.name, genre=game.genre, thumbnail_url=game.thumbnail_url)
            if game
            else None,
        )


class RecommendationMeta(BaseModel):
    used_game_count: int = Field(description="취향 계산에 실제 사용된 게임 수")
    unplayed_game_count: int = Field(description="미플레이로 취향 계산에서 제외된 게임 수")


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendedGame]
    meta: RecommendationMeta

    @classmethod
    def from_result(cls, result: UserRecommendations) -> "RecommendationResponse":
        return cls(
            recommendations=[RecommendedGame.from_detail(d) for d in result.items],
            meta=RecommendationMeta(
                used_game_count=result.used_game_count,
                unplayed_game_count=result.unplayed_game_count,
            ),
        )


class ErrorResponse(BaseModel):
    """Spring ErrorResponse와 같은 형식. code는 분기용 식별자, error는 화면 표시용 문구."""

    code: str
    error: str

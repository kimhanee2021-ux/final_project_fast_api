from dataclasses import dataclass

from app.domain.recommender import Recommendation, Recommender
from app.domain.repositories import (
    GameCatalogRepository,
    GameSummary,
    LibraryRepository,
    UserNotFoundError,
    UserRepository,
)


@dataclass(frozen=True)
class RecommendedGameDetail:
    rank: int
    recommendation: Recommendation
    game: GameSummary | None  # games 카탈로그에 없으면 None


@dataclass(frozen=True)
class UserRecommendations:
    items: list[RecommendedGameDetail]
    used_game_count: int
    unplayed_game_count: int


class RecommendationService:
    """DB의 보유 게임에서 미플레이 게임을 걸러내 추천하고 게임 정보를 붙인다.
    구현체(DB, 모델)는 인터페이스로만 알고 있다."""

    def __init__(
        self,
        recommender: Recommender,
        users: UserRepository,
        library: LibraryRepository,
        catalog: GameCatalogRepository,
    ):
        self._recommender = recommender
        self._users = users
        self._library = library
        self._catalog = catalog

    def recommend_for_user(self, user_id: int, limit: int) -> UserRecommendations:
        if not self._users.exists(user_id):
            raise UserNotFoundError

        owned = self._library.list_owned_games(user_id)
        played = [g for g in owned if g.playtime_hours > 0]
        owned_ids = {g.app_id for g in owned}  # 미플레이 게임도 이미 가진 게임이므로 추천에서 제외

        result = self._recommender.recommend(played, owned_ids, limit)
        games = self._catalog.find_by_app_ids([r.app_id for r in result.items])
        items = [
            RecommendedGameDetail(rank, r, games.get(r.app_id))
            for rank, r in enumerate(result.items, start=1)
        ]
        return UserRecommendations(items, len(result.used_app_ids), len(owned) - len(played))

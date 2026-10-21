"""서비스/API 테스트용 인메모리 가짜 구현. 인터페이스(Protocol)만 지키면 서비스는 구현체를 모른다."""
from app.domain.recommender import (
    NoKnownGamesError,
    OwnedGame,
    Recommendation,
    RecommendationResult,
)
from app.domain.repositories import GameSummary


class FakeRecommender:
    def __init__(self, items: list[Recommendation] | None = None):
        self.items = items if items is not None else []
        self.calls: list[tuple[list[OwnedGame], set[int], int]] = []
        self.new_slots_calls: list[int] = []

    def recommend(self, history, exclude_app_ids, limit, new_slots=0) -> RecommendationResult:
        self.calls.append((history, exclude_app_ids, limit))
        self.new_slots_calls.append(new_slots)
        if not history:
            raise NoKnownGamesError
        return RecommendationResult(
            self.items[:limit], used_app_ids=[g.app_id for g in history], ignored_app_ids=[]
        )


class FakeUserRepository:
    def __init__(self, user_ids: set[int]):
        self.user_ids = user_ids

    def exists(self, user_id: int) -> bool:
        return user_id in self.user_ids


class FakeLibraryRepository:
    def __init__(self, libraries: dict[int, list[OwnedGame]]):
        self.libraries = libraries
        self.requested_user_ids: list[int] = []

    def list_owned_games(self, user_id: int) -> list[OwnedGame]:
        self.requested_user_ids.append(user_id)
        return self.libraries.get(user_id, [])


class FakeGameCatalogRepository:
    def __init__(self, games: list[GameSummary]):
        self.games = {g.app_id: g for g in games}

    def find_by_app_ids(self, app_ids: list[int]) -> dict[int, GameSummary]:
        return {a: self.games[a] for a in app_ids if a in self.games}

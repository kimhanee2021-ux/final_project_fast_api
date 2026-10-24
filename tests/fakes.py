"""API 테스트용 가짜 구현. 인터페이스(Protocol)만 지키면 API는 구현체를 모른다."""
from app.domain.recommender import NoKnownGamesError, Recommendation, RecommendationResult


class FakeRecommender:
    def __init__(self, items: list[Recommendation] | None = None):
        self.items = items if items is not None else []
        self.calls: list[tuple[list, set[int], int, int]] = []

    def recommend(self, history, exclude_app_ids, limit, new_slots=0) -> RecommendationResult:
        self.calls.append((history, exclude_app_ids, limit, new_slots))
        if not history:
            raise NoKnownGamesError
        return RecommendationResult(
            self.items[:limit], used_app_ids=[g.app_id for g in history], ignored_app_ids=[]
        )

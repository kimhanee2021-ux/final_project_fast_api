from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class OwnedGame:
    app_id: int
    playtime_hours: float


@dataclass(frozen=True)
class Recommendation:
    app_id: int
    score: float


@dataclass(frozen=True)
class RecommendationResult:
    items: list[Recommendation]
    used_app_ids: list[int]
    ignored_app_ids: list[int] = field(default_factory=list)


class NoKnownGamesError(Exception):
    """모델이 아는 플레이한 게임이 하나도 없어 추천할 수 없다."""


class Recommender(Protocol):
    def recommend(
        self, history: list[OwnedGame], exclude_app_ids: set[int], limit: int
    ) -> RecommendationResult: ...

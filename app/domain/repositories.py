from dataclasses import dataclass
from typing import Protocol

from app.domain.recommender import OwnedGame


@dataclass(frozen=True)
class GameSummary:
    app_id: int
    name: str
    genre: str | None
    thumbnail_url: str | None


class UserNotFoundError(Exception):
    pass


class UserRepository(Protocol):
    def exists(self, user_id: int) -> bool: ...


class LibraryRepository(Protocol):
    def list_owned_games(self, user_id: int) -> list[OwnedGame]:
        """보유 게임 전체. 오래된 플레이 순 → 최근 순 (미플레이 포함)."""
        ...


class GameCatalogRepository(Protocol):
    def find_by_app_ids(self, app_ids: list[int]) -> dict[int, GameSummary]: ...

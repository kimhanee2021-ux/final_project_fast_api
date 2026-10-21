from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.domain.recommender import OwnedGame
from app.domain.repositories import GameSummary


class MysqlUserRepository:
    def __init__(self, session: Session):
        self._session = session

    def exists(self, user_id: int) -> bool:
        row = self._session.execute(
            text("SELECT 1 FROM users WHERE id = :id"), {"id": user_id}
        ).first()
        return row is not None


class MysqlLibraryRepository:
    """library_games 테이블. playtime_forever는 스팀 원본 값(분)이다."""

    def __init__(self, session: Session):
        self._session = session

    def list_owned_games(self, user_id: int) -> list[OwnedGame]:
        rows = self._session.execute(
            text(
                "SELECT app_id, playtime_forever FROM library_games WHERE user_id = :uid "
                "ORDER BY last_played_at IS NOT NULL, last_played_at ASC"  # 플레이 기록 없는 게임이 가장 앞
            ),
            {"uid": user_id},
        )
        return [OwnedGame(r.app_id, r.playtime_forever / 60) for r in rows]


class MysqlGameCatalogRepository:
    def __init__(self, session: Session):
        self._session = session

    def find_by_app_ids(self, app_ids: list[int]) -> dict[int, GameSummary]:
        if not app_ids:
            return {}
        stmt = text(
            "SELECT app_id, name, genre, thumbnail_url FROM games WHERE app_id IN :ids"
        ).bindparams(bindparam("ids", expanding=True))
        rows = self._session.execute(stmt, {"ids": app_ids})
        return {r.app_id: GameSummary(r.app_id, r.name, r.genre, r.thumbnail_url) for r in rows}

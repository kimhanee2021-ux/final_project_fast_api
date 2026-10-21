import json
from pathlib import Path

from app.domain.recommender import (
    NoKnownGamesError,
    OwnedGame,
    RecommendationResult,
)
from app.infrastructure.game_index import GameIndex
from app.infrastructure.user_encoder import UserEncoder


class TwoTowerRecommender:
    """유저 인코딩(UserEncoder)과 게임 검색(GameIndex)을 이어 붙이는 Recommender 구현체."""

    def __init__(self, model_dir: Path):
        meta = json.loads((model_dir / "meta.json").read_text(encoding="utf-8"))
        self.hist_len: int = meta["hist_len"]
        self._games = GameIndex(model_dir)
        self._encoder = UserEncoder(model_dir, self.hist_len)

    def recommend(
        self, history: list[OwnedGame], exclude_app_ids: set[int], limit: int
    ) -> RecommendationResult:
        ignored = [g.app_id for g in history if self._games.row_of(g.app_id) is None]
        known = [g for g in history if self._games.row_of(g.app_id) is not None][-self.hist_len :]
        if not known:
            raise NoKnownGamesError

        user_vec = self._encoder.encode(
            [g.app_id for g in known],
            [self._games.row_of(g.app_id) for g in known],
            [g.playtime_hours for g in known],
        )
        used_ids = {g.app_id for g in known}
        items = self._games.top(user_vec, exclude_app_ids | used_ids, limit)
        return RecommendationResult(items, sorted(used_ids), ignored)

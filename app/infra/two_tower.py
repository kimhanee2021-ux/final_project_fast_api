import json
from pathlib import Path

from app.domain.recommender import (
    NoKnownGamesError,
    OwnedGame,
    RecommendationResult,
)
from app.infra.game_index import GameIndex
from app.infra.user_encoder import UserEncoder


class TwoTowerRecommender:
    """유저 인코딩(UserEncoder)과 게임 검색(GameIndex)을 이어 붙이는 Recommender 구현체."""

    def __init__(self, model_dir: Path):
        meta = json.loads((model_dir / "meta.json").read_text(encoding="utf-8"))
        self.hist_len: int = meta["hist_len"]
        self._games = GameIndex(model_dir)
        self._encoder = UserEncoder(model_dir, self.hist_len)

    def recommend(
        self, history: list[OwnedGame], exclude_app_ids: set[int], limit: int, new_slots: int = 0
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
        exclude = exclude_app_ids | used_ids
        new_slots = min(new_slots, limit) if self._games.has_new_slots else 0  # 파일이 없으면 신작 칸은 쓰지 않는다
        if new_slots == 0:
            items = self._games.top(user_vec, exclude, limit)
        else:  # 기본 칸은 학습에 있던 게임에서, 신작 칸은 학습에 없던 게임에서 뽑아 구성을 보장한다
            items = self._games.top(user_vec, exclude, limit - new_slots, only="trained")
            items += self._games.top(user_vec, exclude, new_slots, only="new")
        return RecommendationResult(items, sorted(used_ids), ignored)

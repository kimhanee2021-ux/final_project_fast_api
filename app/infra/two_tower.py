import json
from pathlib import Path

from app.domain.recommender import (
    NoKnownGamesError,
    OwnedGame,
    RecommendationResult,
)
from app.infra.game_index import GameIndex
from app.infra.user_encoder import UserEncoder


def _latest_per_game(history: list[OwnedGame]) -> list[OwnedGame]:
    """같은 게임이 여러 번 오면 마지막 것만 남긴다 (순서는 마지막으로 나온 순).
    유저 타워는 칸마다 게임을 따로 보므로, 중복되면 한 게임이 두 번 반영된다."""
    seen: set[int] = set()
    kept = []
    for game in reversed(history):
        if game.app_id not in seen:
            seen.add(game.app_id)
            kept.append(game)
    return kept[::-1]


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
        history = _latest_per_game(history)
        ignored = [g.app_id for g in history if self._games.row_of(g.app_id) is None]
        known = [g for g in history if self._games.row_of(g.app_id) is not None][-self.hist_len :]
        if not known:
            raise NoKnownGamesError

        user_vec = self._encoder.encode(
            [self._games.row_of(g.app_id) for g in known],
            [g.playtime_hours for g in known],
        )
        used_ids = {g.app_id for g in known}
        exclude = exclude_app_ids | used_ids
        new_slots = min(new_slots, limit)
        if new_slots == 0:
            items = self._games.top(user_vec, exclude, limit)
        else:  # 기본 칸은 학습에 있던 게임에서, 신작 칸은 학습에 없던 게임에서 뽑아 구성을 보장한다
            items = self._games.top(user_vec, exclude, limit - new_slots, only="trained")
            items += self._games.top(user_vec, exclude, new_slots, only="new")
        return RecommendationResult(items, sorted(used_ids), ignored)

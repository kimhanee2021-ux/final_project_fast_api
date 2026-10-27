from pathlib import Path

import numpy as np

from app.domain.recommender import Recommendation


class GameIndex:
    """미리 계산된 게임 벡터와 app_id <-> 행 번호 대응, 추천 후보 필터링.
    신작 칸(학습 기록에 없던 게임)은 in_train.npy로 가른다. 게임 벡터가 하나뿐이라 신작도 과거작과 같은 벡터로 점수를 낸다."""

    def __init__(self, model_dir: Path):
        self._game_vecs = np.load(model_dir / "game_vecs.npy")
        self.entity_app_ids = np.load(model_dir / "entity_app_ids.npy")
        # 콘텐츠 행 번호 = entity_app_ids 위치 + 1 (0은 빈칸)
        self._row_of_app = {int(a): i + 1 for i, a in enumerate(self.entity_app_ids)}
        mask_path = model_dir / "candidate_mask.npy"
        self._allowed = np.load(mask_path) if mask_path.exists() else None
        self._is_new = ~np.load(model_dir / "in_train.npy")  # True = 학습에 없던 게임

    def row_of(self, app_id: int) -> int | None:
        return self._row_of_app.get(app_id)

    def top(
        self,
        user_vec: np.ndarray,
        exclude_app_ids: set[int],
        limit: int,
        *,
        only: str | None = None,  # None = 전체, "trained" = 학습에 있던 게임만, "new" = 학습에 없던 게임만
    ) -> list[Recommendation]:
        scores = self._game_vecs @ user_vec
        if self._allowed is not None:
            scores = np.where(self._allowed, scores, -np.inf)
        if only is not None:
            scores = np.where(self._is_new if only == "new" else ~self._is_new, scores, -np.inf)
        for app_id in exclude_app_ids:
            row = self._row_of_app.get(app_id)
            if row is not None:
                scores[row - 1] = -np.inf

        limit = min(limit, len(scores) - 1)
        top = np.argpartition(-scores, limit)[:limit]
        top = top[np.argsort(-scores[top])]
        return [
            Recommendation(int(self.entity_app_ids[i]), float(scores[i]), "new" if only == "new" else "main")
            for i in top
            if np.isfinite(scores[i])
        ]

from pathlib import Path

import numpy as np

from app.domain.recommender import Recommendation


class GameIndex:
    """미리 계산된 게임 벡터와 app_id <-> 행 번호 대응, 추천 후보 필터링."""

    def __init__(self, model_dir: Path):
        self._game_vecs = np.load(model_dir / "game_vecs.npy")
        self.entity_app_ids = np.load(model_dir / "entity_app_ids.npy")
        # 콘텐츠 행 번호 = entity_app_ids 위치 + 1 (0은 빈칸)
        self._row_of_app = {int(a): i + 1 for i, a in enumerate(self.entity_app_ids)}
        mask_path = model_dir / "candidate_mask.npy"
        self._allowed = np.load(mask_path) if mask_path.exists() else None
        # 신작 칸용 (선택): 콘텐츠만으로 만든 게임 벡터와, 학습에 없던 게임 표시. 두 파일이 모두 있어야 켜진다
        content_path = model_dir / "game_vecs_content.npy"
        gid_path = model_dir / "gid_of_row.npy"
        has_new = content_path.exists() and gid_path.exists()
        self._content_vecs = np.load(content_path) if has_new else None
        self._is_new = (np.load(gid_path)[1:] == 0) if has_new else None  # True = 학습에 없던 게임

    @property
    def has_new_slots(self) -> bool:
        return self._content_vecs is not None

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
        content = only == "new"  # 신작은 ID 벡터가 없으므로 콘텐츠만으로 만든 벡터로 점수를 낸다
        scores = (self._content_vecs if content else self._game_vecs) @ user_vec
        if self._allowed is not None:
            scores = np.where(self._allowed, scores, -np.inf)
        if only is not None:
            if self._is_new is None:
                raise ValueError("신작 칸 파일(game_vecs_content.npy, gid_of_row.npy)이 없다")
            scores = np.where(self._is_new if only == "new" else ~self._is_new, scores, -np.inf)
        for app_id in exclude_app_ids:
            row = self._row_of_app.get(app_id)
            if row is not None:
                scores[row - 1] = -np.inf

        limit = min(limit, len(scores) - 1)
        top = np.argpartition(-scores, limit)[:limit]
        top = top[np.argsort(-scores[top])]
        return [
            Recommendation(int(self.entity_app_ids[i]), float(scores[i]), "new" if content else "main")
            for i in top
            if np.isfinite(scores[i])
        ]

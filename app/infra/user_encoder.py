import math
import os
import threading
from pathlib import Path

import numpy as np


class UserEncoder:
    """보유 게임 이력을 유저 타워에 넣어 사용자 벡터로 만든다."""

    def __init__(self, model_dir: Path, hist_len: int):
        # keras는 무거워서 이 모듈을 import 할 때가 아니라 모델을 만들 때 불러온다.
        # 백엔드는 keras를 import 하기 전에 정해야 한다.
        os.environ.setdefault("KERAS_BACKEND", "torch")
        import keras

        self._keras = keras
        self.hist_len = hist_len
        self._user_tower = keras.saving.load_model(model_dir / "user_tower.keras", compile=False)
        item_ids = np.load(model_dir / "item_ids.npy")
        # 학습 게임 번호 = item_ids 위치 + 1 (0은 학습에 없음)
        self._gid_of_app = {int(a): i + 1 for i, a in enumerate(item_ids)}
        self._lock = threading.Lock()

    def encode(self, app_ids: list[int], rows: list[int], playtime_hours: list[float]) -> np.ndarray:
        hist_row = np.zeros((1, self.hist_len), dtype=np.int32)
        hist_gid = np.zeros((1, self.hist_len), dtype=np.int32)
        weight = np.zeros((1, self.hist_len), dtype=np.float32)
        for i, (app_id, row, hours) in enumerate(zip(app_ids, rows, playtime_hours)):
            hist_row[0, i] = row
            hist_gid[0, i] = self._gid_of_app.get(app_id, 0)
            weight[0, i] = 1.0 + math.log1p(hours)
        weight /= weight.sum()
        with self._lock:
            out = self._user_tower({"hist_row": hist_row, "hist_gid": hist_gid, "weight": weight})
        return np.asarray(self._keras.ops.convert_to_numpy(out))[0]

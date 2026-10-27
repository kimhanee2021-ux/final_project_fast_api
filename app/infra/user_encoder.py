import math
import os
import threading
from pathlib import Path

import numpy as np


class UserEncoder:
    """보유 게임 이력을 유저 타워(어텐션 모델)에 넣어 사용자 벡터로 만든다.
    입력은 hist_row(게임 행 번호)와 weight(플레이 시간 가중치)뿐이고, 게임 ID는 쓰지 않는다."""

    def __init__(self, model_dir: Path, hist_len: int):
        # keras는 무거워서 이 모듈을 import 할 때가 아니라 모델을 만들 때 불러온다.
        # 백엔드는 keras를 import 하기 전에 정해야 한다.
        os.environ.setdefault("KERAS_BACKEND", "torch")
        import keras

        self._keras = keras
        self.hist_len = hist_len
        self._user_tower = keras.saving.load_model(model_dir / "user_tower.keras", compile=False)
        self._lock = threading.Lock()

    def encode(self, rows: list[int], playtime_hours: list[float]) -> np.ndarray:
        hist_row = np.zeros((1, self.hist_len), dtype=np.int32)
        weight = np.zeros((1, self.hist_len), dtype=np.float32)
        for i, (row, hours) in enumerate(zip(rows, playtime_hours)):
            hist_row[0, i] = row
            weight[0, i] = 1.0 + math.log1p(hours)
        weight /= weight.sum()
        with self._lock:
            out = self._user_tower({"hist_row": hist_row, "weight": weight})
        return np.asarray(self._keras.ops.convert_to_numpy(out))[0]

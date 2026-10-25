import json
from pathlib import Path

import numpy as np

POOL = 300  # 임베딩 유사도 상위 후보 수
TAG_POOL = 2000  # 태그가 일치하는 게임 중 후보에 추가할 최대 개수
POP_WEIGHT = 0.7  # 인기도(log 리뷰 수) 반영 정도
TAG_WEIGHT = 3.0  # 태그 일치 가산점 크기

_NO_ROWS = np.array([], dtype=np.int64)


class SearchIndex:
    """검색 대상 게임의 임베딩과 태그·리뷰 수. 질의 벡터가 주어지면 점수를 매겨 상위 게임을 고른다 (numpy만 사용).

    점수 = z(유사도) + POP_WEIGHT * z(log10 리뷰 수) + TAG_WEIGHT * 태그 일치(0~1).
    z()는 후보 안에서 평균 0, 표준편차 1로 맞춘 값이다. 규칙은 학습 쪽 nl_search_v5.ipynb와 같다.
    """

    def __init__(self, emb, app_ids, names, tags, reviews, tag_idf: dict[str, float]):
        self._emb = np.asarray(emb, dtype=np.float32)
        self._app_ids = np.asarray(app_ids, dtype=np.int64)
        self._names = [n.lower() for n in names]
        self._reviews = np.asarray(reviews, dtype=np.int64)
        self._logrev = np.log10(self._reviews + 1.0)
        self._tag_idf = tag_idf
        self._tag_of_lower = {t.lower(): t for t in tag_idf}
        rows: dict[str, list[int]] = {}
        for i, game_tags in enumerate(tags):
            for t in set(game_tags):
                rows.setdefault(t, []).append(i)
        self._rows_of_tag = {t: np.array(v, dtype=np.int64) for t, v in rows.items()}

    @classmethod
    def load(cls, search_dir: Path) -> "SearchIndex":
        games = json.loads((search_dir / "games.json").read_text(encoding="utf-8"))
        tag_idf = json.loads((search_dir / "tag_idf.json").read_text(encoding="utf-8"))
        emb = np.load(search_dir / "emb.npy")
        return cls(emb, games["app_ids"], games["names"], games["tags"], games["reviews"], tag_idf)

    def __len__(self) -> int:
        return len(self._app_ids)

    def resolve_tags(self, names: list[str]) -> tuple[list[str], list[str]]:
        """요청의 태그 이름 -> (데이터의 정확한 태그 이름, 못 찾은 이름). 대소문자는 구분하지 않는다."""
        valid: list[str] = []
        ignored: list[str] = []
        for name in names:
            tag = self._tag_of_lower.get(name.strip().lower())
            if tag is None:
                ignored.append(name)
            elif tag not in valid:
                valid.append(tag)
        return valid, ignored

    def find_game(self, name: str) -> int | None:
        """게임 이름 -> 행 번호. 이름이 정확히 같은 게임을 먼저, 없으면 이름에 포함된 게임 중 리뷰가 가장 많은 것."""
        needle = name.strip().lower()
        if not needle:
            return None
        hits = [i for i, n in enumerate(self._names) if n == needle]
        hits = hits or [i for i, n in enumerate(self._names) if needle in n]
        return max(hits, key=lambda i: self._reviews[i]) if hits else None

    def app_id_of(self, row: int) -> int:
        return int(self._app_ids[row])

    def vector_of(self, row: int) -> np.ndarray:
        return self._emb[row]

    def search(
        self,
        query_vec: np.ndarray,
        tags: list[str],
        exclude_tags: list[str],
        limit: int,
        exclude_row: int | None = None,
    ) -> list[tuple[int, float]]:
        """(app_id, 점수) 목록. 점수가 높은 순. tags/exclude_tags는 resolve_tags를 거친 이름이어야 한다."""
        sims = self._emb @ np.asarray(query_vec, dtype=np.float32)

        allowed = np.ones(len(self), dtype=bool)
        for tag in exclude_tags:
            allowed[self._rows_of_tag.get(tag, _NO_ROWS)] = False
        if exclude_row is not None:
            allowed[exclude_row] = False
        sims[~allowed] = -1.0

        # 태그 일치도(0~1): 요청한 태그 중 게임이 가진 태그의 IDF 합 / 요청한 태그의 IDF 합 (드문 태그일수록 큼)
        match = np.zeros(len(self), dtype=np.float32)
        total = sum(self._tag_idf[t] for t in tags)
        if tags and total > 0:
            for tag in tags:
                match[self._rows_of_tag.get(tag, _NO_ROWS)] += self._tag_idf[tag]
            match /= total

        pool = set(np.argsort(-sims)[:POOL].tolist())  # 임베딩 유사도 상위 후보
        if tags:  # 태그가 일치하는 게임은 유사도 상위 밖이어도 후보에 넣는다
            tagged = np.where((match > 0) & allowed)[0]
            pool |= set(tagged[np.argsort(-sims[tagged])[:TAG_POOL]].tolist())
        idx = np.array(sorted(pool), dtype=np.int64)
        idx = idx[allowed[idx]]
        if idx.size == 0:
            return []

        def z(x: np.ndarray) -> np.ndarray:
            return (x - x.mean()) / (x.std() + 1e-9)

        score = z(sims[idx]) + POP_WEIGHT * z(self._logrev[idx]) + TAG_WEIGHT * match[idx]
        best = np.argsort(-score)[:limit]
        return [(int(self._app_ids[idx[b]]), float(score[b])) for b in best]

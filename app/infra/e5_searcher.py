from pathlib import Path

import numpy as np

from app.domain.searcher import NoSearchKeywordsError, SearchItem, SearchKeywords, SearchResult
from app.infra.query_encoder import QueryEncoder
from app.infra.search_index import SearchIndex


class E5Searcher:
    """Searcher 구현체. 키워드를 질의 벡터 하나로 만들고(QueryEncoder), 점수 계산은 SearchIndex가 한다."""

    def __init__(self, search_dir: Path, encoder_name: str):
        self._index = SearchIndex.load(search_dir)
        self._encoder = QueryEncoder(encoder_name)

    def search(self, keywords: SearchKeywords, limit: int) -> SearchResult:
        tags, ignored = self._index.resolve_tags(keywords.tags)
        exclude_tags, ignored_exclude = self._index.resolve_tags(keywords.exclude_tags)

        similar_row = self._index.find_game(keywords.similar_to) if keywords.similar_to else None

        # 질의 벡터: 설명 문장, 비슷한 게임의 벡터를 평균낸다. 둘 다 없으면 태그 이름을 이어 붙여 쓴다
        vectors: list[np.ndarray] = []
        if keywords.description.strip():
            vectors.append(self._encoder.encode(keywords.description.strip()))
        if similar_row is not None:
            vectors.append(self._index.vector_of(similar_row))
        if not vectors and tags:
            vectors.append(self._encoder.encode(", ".join(tags)))
        if not vectors:
            raise NoSearchKeywordsError

        query = np.mean(vectors, axis=0)
        query = query / (np.linalg.norm(query) + 1e-12)

        found = self._index.search(query, tags, exclude_tags, limit, exclude_row=similar_row)
        return SearchResult(
            items=[SearchItem(app_id, score) for app_id, score in found],
            ignored_tags=ignored + ignored_exclude,
            similar_to_app_id=None if similar_row is None else self._index.app_id_of(similar_row),
        )

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SearchKeywords:
    """Spring이 LLM으로 뽑아 넘기는 영어 키워드. 비어 있는 항목은 쓰지 않는다."""

    tags: list[str] = field(default_factory=list)  # 원하는 Steam 태그. 가진 게임에 가산점
    exclude_tags: list[str] = field(default_factory=list)  # 이 태그를 가진 게임은 결과에서 뺀다
    description: str = ""  # 원하는 게임을 설명하는 영어 한 문장
    similar_to: str = ""  # "OO 같은 게임"일 때 그 게임의 영어 이름


@dataclass(frozen=True)
class SearchItem:
    app_id: int
    score: float


@dataclass(frozen=True)
class SearchResult:
    items: list[SearchItem]
    ignored_tags: list[str] = field(default_factory=list)  # 데이터에 없어서 무시한 태그 (대소문자 보정 후에도 못 찾은 것)
    similar_to_app_id: int | None = None  # similar_to로 찾은 게임. 못 찾았거나 요청에 없으면 None


class NoSearchKeywordsError(Exception):
    """쓸 수 있는 키워드(태그, 설명, 비슷한 게임)가 하나도 없어 검색할 수 없다."""


class SearchUnavailableError(Exception):
    """검색 모델 파일이 없어 서버가 검색 없이 시작됐다."""


class Searcher(Protocol):
    def search(self, keywords: SearchKeywords, limit: int) -> SearchResult: ...

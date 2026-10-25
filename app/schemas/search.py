from pydantic import BaseModel, Field

from app.core.config import DEFAULT_SEARCH_RESULTS, MAX_SEARCH_KEYWORDS, MAX_SEARCH_RESULTS
from app.domain.searcher import SearchItem, SearchKeywords, SearchResult


class SearchRequest(BaseModel):
    tags: list[str] = Field(
        default_factory=list,
        max_length=MAX_SEARCH_KEYWORDS,
        description="원하는 Steam 태그(영어). 가진 게임에 가산점. 대소문자는 구분하지 않고, 없는 태그는 무시한다",
    )
    exclude_tags: list[str] = Field(
        default_factory=list, max_length=MAX_SEARCH_KEYWORDS, description="이 태그를 가진 게임은 결과에서 뺀다"
    )
    description: str = Field("", max_length=500, description="원하는 게임을 설명하는 영어 한 문장")
    similar_to: str = Field("", max_length=200, description="'OO 같은 게임'일 때 그 게임의 영어 이름")
    limit: int = Field(DEFAULT_SEARCH_RESULTS, ge=1, le=MAX_SEARCH_RESULTS)

    def to_domain(self) -> SearchKeywords:
        return SearchKeywords(self.tags, self.exclude_tags, self.description, self.similar_to)


class SearchItemOut(BaseModel):
    app_id: int
    score: float = Field(description="요청 내 순위용 점수 (확률/일치율 아님)")

    @classmethod
    def from_domain(cls, item: SearchItem) -> "SearchItemOut":
        return cls(app_id=item.app_id, score=round(item.score, 4))


class SearchResponse(BaseModel):
    items: list[SearchItemOut] = Field(description="점수가 높은 순")
    ignored_tags: list[str] = Field(description="데이터에 없어서 무시한 태그 (tags, exclude_tags 모두)")
    similar_to_app_id: int | None = Field(description="similar_to로 찾은 게임. 요청에 없거나 못 찾았으면 null")

    @classmethod
    def from_result(cls, result: SearchResult) -> "SearchResponse":
        return cls(
            items=[SearchItemOut.from_domain(i) for i in result.items],
            ignored_tags=result.ignored_tags,
            similar_to_app_id=result.similar_to_app_id,
        )

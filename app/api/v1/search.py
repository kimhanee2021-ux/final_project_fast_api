from fastapi import APIRouter, Depends

from app.api.dependencies import get_searcher
from app.domain.searcher import Searcher
from app.schemas.recommendation import ErrorResponse
from app.schemas.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "",
    response_model=SearchResponse,
    summary="LLM이 뽑은 키워드로 게임 검색 (내부 API)",
    responses={
        422: {"model": ErrorResponse, "description": "쓸 수 있는 키워드가 없음 (NO_SEARCH_KEYWORDS)"},
        503: {"model": ErrorResponse, "description": "검색 모델 파일이 없어 검색을 쓸 수 없음 (SEARCH_UNAVAILABLE)"},
    },
)
def search(body: SearchRequest, searcher: Searcher = Depends(get_searcher)) -> SearchResponse:
    return SearchResponse.from_result(searcher.search(body.to_domain(), body.limit))

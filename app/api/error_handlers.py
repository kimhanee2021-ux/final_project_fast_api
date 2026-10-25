"""모든 에러 응답을 { "code": ..., "error": ... } 로 내린다. 호출하는 Spring이 code로 분기한다."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.recommender import NoKnownGamesError
from app.domain.searcher import NoSearchKeywordsError, SearchUnavailableError

logger = logging.getLogger(__name__)


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "error": message})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NoKnownGamesError)
    async def no_known_games(_: Request, __: NoKnownGamesError):
        return error_response(422, "NO_KNOWN_GAMES", "모델이 아는 플레이한 게임이 없어 추천할 수 없습니다")

    @app.exception_handler(NoSearchKeywordsError)
    async def no_search_keywords(_: Request, __: NoSearchKeywordsError):
        return error_response(422, "NO_SEARCH_KEYWORDS", "쓸 수 있는 태그, 설명, 비슷한 게임이 없어 검색할 수 없습니다")

    @app.exception_handler(SearchUnavailableError)
    async def search_unavailable(_: Request, __: SearchUnavailableError):
        return error_response(503, "SEARCH_UNAVAILABLE", "검색 모델이 준비되지 않았습니다")

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, e: RequestValidationError):
        message = ", ".join(f"{'.'.join(map(str, x['loc'][1:]))}: {x['msg']}" for x in e.errors())
        return error_response(400, "VALIDATION_ERROR", message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, e: StarletteHTTPException):
        return error_response(e.status_code, f"HTTP_{e.status_code}", str(e.detail))

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, e: Exception):
        logger.exception("처리되지 않은 예외", exc_info=e)
        return error_response(500, "INTERNAL_ERROR", "서버 내부 오류가 발생했습니다")

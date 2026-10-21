"""모든 에러 응답을 Spring ErrorResponse와 같은 { "code": ..., "error": ... } 로 내린다.

프론트는 code/error로 분기한다. 추천 요청은 skipSessionExpiry라 이 서버의 401로 로그아웃되지 않지만,
토큰 문제만 401로 내리고 서버 오류는 401로 내리지 않는다는 Spring의 규칙은 그대로 지킨다.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.auth import InvalidTokenError
from app.domain.recommender import NoKnownGamesError
from app.domain.repositories import UserNotFoundError

logger = logging.getLogger(__name__)


def error_response(
    status: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "error": message}, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidTokenError)
    async def invalid_token(_: Request, __: InvalidTokenError):
        return error_response(401, "UNAUTHENTICATED", "로그인이 필요합니다", {"WWW-Authenticate": "Bearer"})

    @app.exception_handler(UserNotFoundError)
    async def user_not_found(_: Request, __: UserNotFoundError):
        return error_response(404, "USER_NOT_FOUND", "존재하지 않는 회원입니다")

    @app.exception_handler(NoKnownGamesError)
    async def no_played_games(_: Request, __: NoKnownGamesError):
        return error_response(
            409,
            "NO_PLAYED_GAMES",
            "추천에 사용할 수 있는 플레이한 게임이 없습니다. 스팀 라이브러리를 동기화했는지 확인하세요.",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, e: RequestValidationError):
        message = ", ".join(f"{'.'.join(map(str, x['loc'][1:]))}: {x['msg']}" for x in e.errors())
        return error_response(400, "VALIDATION_ERROR", message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, e: StarletteHTTPException):
        return error_response(e.status_code, f"HTTP_{e.status_code}", str(e.detail), dict(e.headers or {}))

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, e: Exception):
        logger.exception("처리되지 않은 예외", exc_info=e)
        return error_response(500, "INTERNAL_ERROR", "서버 내부 오류가 발생했습니다")

import logging

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.auth import InvalidTokenError, TokenVerifier
from app.infrastructure.jwt_verifier import JwtTokenVerifier

logger = logging.getLogger("uvicorn.error")
bearer_scheme = HTTPBearer(auto_error=False)


def get_token_verifier(request: Request) -> TokenVerifier:
    return JwtTokenVerifier(request.app.state.settings.jwt_secret_key)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    verifier: TokenVerifier = Depends(get_token_verifier),
) -> int:
    """Authorization: Bearer <토큰> 에서 로그인한 유저 id를 꺼낸다."""
    if credentials is None:
        logger.warning("토큰 거부: Authorization: Bearer 헤더가 없음")
        raise InvalidTokenError
    return verifier.verify(credentials.credentials)

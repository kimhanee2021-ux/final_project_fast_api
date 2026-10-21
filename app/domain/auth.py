from typing import Protocol


class InvalidTokenError(Exception):
    """토큰이 없거나 서명/만료가 올바르지 않다."""


class TokenVerifier(Protocol):
    def verify(self, token: str) -> int:
        """유효한 토큰이면 로그인한 유저 id를 돌려준다."""
        ...

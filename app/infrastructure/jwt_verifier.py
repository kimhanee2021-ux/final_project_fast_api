import logging

import jwt

from app.domain.auth import InvalidTokenError


logger = logging.getLogger("uvicorn.error")

# jjwt의 signWith(key)는 키 길이로 알고리즘을 고른다: 32바이트↑ HS256, 48↑ HS384, 64↑ HS512.
# (같은 비밀키만 쓰는 대칭 HMAC 계열만 허용한다. none/RSA 등은 받지 않는다)
_HMAC_ALGORITHMS = ["HS256", "HS384", "HS512"]


class JwtTokenVerifier:
    """Spring JwtService가 발급한 액세스 토큰(HMAC 서명, subject = 유저 id)을 검증한다."""

    def __init__(self, secret_key: str):
        self._key = secret_key.encode("utf-8")

    def verify(self, token: str) -> int:
        try:
            claims = jwt.decode(
                token, self._key, algorithms=_HMAC_ALGORITHMS, options={"require": ["sub", "exp"]}
            )
            # 소셜 연동용 단기 상태 토큰(purpose claim)은 액세스 토큰이 아니므로 거부
            if "purpose" in claims:
                logger.warning("토큰 거부: 액세스 토큰이 아님(purpose=%s)", claims["purpose"])
                raise InvalidTokenError
            return int(claims["sub"])
        except (jwt.PyJWTError, ValueError) as e:
            logger.warning("토큰 거부: %s: %s", type(e).__name__, e)  # 토큰 값은 남기지 않는다
            raise InvalidTokenError from e

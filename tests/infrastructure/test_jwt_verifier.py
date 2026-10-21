import time

import jwt
import pytest

from app.domain.auth import InvalidTokenError
from app.infrastructure.jwt_verifier import JwtTokenVerifier
from tests.support import TEST_JWT_SECRET

KEY = TEST_JWT_SECRET.encode("utf-8")
verifier = JwtTokenVerifier(TEST_JWT_SECRET)


def make_token(key=KEY, algorithm="HS512", **claims) -> str:
    now = int(time.time())
    payload = {"sub": "42", "iat": now, "exp": now + 600, **claims}
    payload = {k: v for k, v in payload.items() if v is not None}
    return jwt.encode(payload, key, algorithm=algorithm)


@pytest.mark.parametrize("algorithm", ["HS256", "HS384", "HS512"])
def test_valid_token_returns_user_id_for_every_hmac_algorithm(algorithm):
    # Spring(jjwt)은 비밀키 길이에 따라 HS256/384/512 중 하나로 서명한다
    assert verifier.verify(make_token(algorithm=algorithm)) == 42


def test_token_signed_with_other_secret_is_rejected():
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(key=b"another-secret-" * 5))


def test_expired_token_is_rejected():
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(exp=int(time.time()) - 10))


def test_token_without_expiry_is_rejected():
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(exp=None))


def test_token_without_subject_is_rejected():
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(sub=None))


def test_non_numeric_subject_is_rejected():
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(sub="not-a-number"))


def test_state_token_with_purpose_is_not_an_access_token():
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(purpose="steam-link"))


def test_unsigned_alg_none_token_is_rejected():
    unsigned = jwt.encode({"sub": "42", "exp": int(time.time()) + 600}, None, algorithm="none")
    with pytest.raises(InvalidTokenError):
        verifier.verify(unsigned)


def test_garbage_is_rejected():
    with pytest.raises(InvalidTokenError):
        verifier.verify("not.a.jwt")

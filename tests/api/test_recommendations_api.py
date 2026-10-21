import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_recommendation_service
from app.domain.recommender import OwnedGame, Recommendation
from app.domain.repositories import GameSummary
from app.main import create_app
from app.services.recommendation_service import RecommendationService
from tests.support import TEST_JWT_SECRET, make_test_settings
from tests.fakes import (
    FakeGameCatalogRepository,
    FakeLibraryRepository,
    FakeRecommender,
    FakeUserRepository,
)

URL = "/api/v1/users/me/recommendations"
USER_ID = 5
OTHER_USER_ID = 6


def bearer(user_id: int = USER_ID, secret: str = TEST_JWT_SECRET, **claims) -> dict[str, str]:
    now = int(time.time())
    payload = {"sub": str(user_id), "iat": now, "exp": now + 600, **claims}
    return {"Authorization": "Bearer " + jwt.encode(payload, secret, algorithm="HS512")}


@pytest.fixture
def library():
    return FakeLibraryRepository(
        {
            USER_ID: [OwnedGame(100, 30.0), OwnedGame(300, 0)],
            OTHER_USER_ID: [OwnedGame(999, 5.0)],
        }
    )


@pytest.fixture
def client(library):
    # 앱마다 새로 조립한다. lifespan(실제 모델 로딩)을 돌리지 않도록 with 없이 쓰고, 서비스만 가짜로 갈아 끼운다
    service = RecommendationService(
        recommender=FakeRecommender([Recommendation(11, 0.91234567), Recommendation(22, 0.5)]),
        users=FakeUserRepository({USER_ID, OTHER_USER_ID}),
        library=library,
        catalog=FakeGameCatalogRepository([GameSummary(11, "Game 11", "RPG", "http://img/11")]),
    )
    app = create_app(make_test_settings())
    app.dependency_overrides[get_recommendation_service] = lambda: service
    return TestClient(app)


def test_returns_recommendations_with_game_info_and_meta(client):
    response = client.get(URL, headers=bearer())

    assert response.status_code == 200
    assert response.json() == {
        "recommendations": [
            {
                "rank": 1,
                "app_id": 11,
                "score": 0.9123,
                "source": "main",
                "game": {"name": "Game 11", "genre": "RPG", "thumbnail_url": "http://img/11"},
            },
            {"rank": 2, "app_id": 22, "score": 0.5, "source": "main", "game": None},
        ],
        "meta": {"used_game_count": 1, "unplayed_game_count": 1},
    }


def test_uses_only_the_logged_in_users_library(client, library):
    client.get(URL, headers=bearer(user_id=OTHER_USER_ID))

    assert library.requested_user_ids == [OTHER_USER_ID]


def test_user_id_in_query_string_cannot_override_the_token(client, library):
    client.get(URL, params={"user_id": OTHER_USER_ID}, headers=bearer(user_id=USER_ID))

    assert library.requested_user_ids == [USER_ID]


def test_limit_is_applied(client):
    response = client.get(URL, params={"limit": 1}, headers=bearer())

    assert [r["app_id"] for r in response.json()["recommendations"]] == [11]


@pytest.mark.parametrize("limit", ["0", "51", "abc"])
def test_invalid_limit_is_400_validation_error(client, limit):
    response = client.get(URL, params={"limit": limit}, headers=bearer())

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer garbage"},
        {"Authorization": "Basic abc"},
        bearer(secret="a-different-secret-a-different-secret-a-different-secret"),
        bearer(purpose="steam-link"),
    ],
    ids=["no-header", "garbage-token", "wrong-scheme", "wrong-secret", "state-token"],
)
def test_missing_or_invalid_token_is_401_unauthenticated(client, headers):
    response = client.get(URL, headers=headers)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHENTICATED", "error": "로그인이 필요합니다"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_valid_token_of_deleted_user_is_404(client):
    response = client.get(URL, headers=bearer(user_id=12345))

    assert response.status_code == 404
    assert response.json()["code"] == "USER_NOT_FOUND"


def test_library_without_played_games_is_409(library, client):
    library.libraries[USER_ID] = [OwnedGame(300, 0)]

    response = client.get(URL, headers=bearer())

    assert response.status_code == 409
    assert response.json()["code"] == "NO_PLAYED_GAMES"


def test_unknown_path_uses_the_same_error_format(client):
    response = client.get("/nope")

    assert response.status_code == 404
    assert set(response.json()) == {"code", "error"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_new_slots_query_is_passed_to_recommender(library):
    recommender = FakeRecommender([Recommendation(11, 0.9), Recommendation(22, 0.5)])
    service = RecommendationService(
        recommender=recommender,
        users=FakeUserRepository({USER_ID}),
        library=library,
        catalog=FakeGameCatalogRepository([]),
    )
    app = create_app(make_test_settings())
    app.dependency_overrides[get_recommendation_service] = lambda: service

    response = TestClient(app).get(URL + "?limit=5&new_slots=2", headers=bearer())

    assert response.status_code == 200
    assert recommender.new_slots_calls[-1] == 2


def test_new_slots_over_max_is_validation_error(client):
    response = client.get(URL + "?new_slots=999", headers=bearer())

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"

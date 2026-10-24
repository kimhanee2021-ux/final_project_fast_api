import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_recommender
from app.domain.recommender import OwnedGame, Recommendation
from app.main import create_app
from tests.fakes import FakeRecommender
from tests.support import make_test_settings

URL = "/internal/v1/recommendations"
BODY = {
    "played_games": [{"app_id": 100, "playtime_hours": 30.0}],
    "exclude_app_ids": [100, 300],
    "limit": 2,
    "new_slots": 1,
}


@pytest.fixture
def recommender():
    return FakeRecommender(
        [Recommendation(11, 0.91234567), Recommendation(22, 0.5, source="new"), Recommendation(33, 0.1)]
    )


@pytest.fixture
def client(recommender):
    # lifespan(실제 모델 로딩)을 돌리지 않도록 with 없이 쓰고, 추천기만 가짜로 갈아 끼운다
    app = create_app(make_test_settings())
    app.dependency_overrides[get_recommender] = lambda: recommender
    return TestClient(app)


def test_returns_ranked_items_with_used_games(client):
    response = client.post(URL, json=BODY)

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"app_id": 11, "score": 0.9123, "source": "main"},
            {"app_id": 22, "score": 0.5, "source": "new"},
        ],
        "used_app_ids": [100],
        "ignored_app_ids": [],
    }


def test_request_is_passed_to_recommender_as_domain_values(client, recommender):
    client.post(URL, json=BODY)

    assert recommender.calls == [([OwnedGame(100, 30.0)], {100, 300}, 2, 1)]


def test_optional_fields_have_defaults(client, recommender):
    client.post(URL, json={"played_games": [{"app_id": 100, "playtime_hours": 1}]})

    assert recommender.calls[-1] == ([OwnedGame(100, 1)], set(), 10, 0)


def test_empty_history_is_422_no_known_games(client):
    response = client.post(URL, json={"played_games": []})

    assert response.status_code == 422
    assert response.json()["code"] == "NO_KNOWN_GAMES"


@pytest.mark.parametrize(
    "patch",
    [
        {"limit": 0},
        {"limit": 51},
        {"new_slots": -1},
        {"new_slots": 51},
        {"played_games": [{"app_id": 1, "playtime_hours": -1}]},
        {"played_games": "abc"},
    ],
)
def test_invalid_body_is_400_validation_error(client, patch):
    response = client.post(URL, json={**BODY, **patch})

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_missing_played_games_is_validation_error(client):
    assert client.post(URL, json={}).json()["code"] == "VALIDATION_ERROR"


def test_unknown_path_uses_the_same_error_format(client):
    response = client.get("/nope")

    assert response.status_code == 404
    assert set(response.json()) == {"code", "error"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_searcher
from app.domain.searcher import SearchItem, SearchKeywords
from app.main import create_app
from tests.fakes import FakeSearcher
from tests.support import make_test_settings

URL = "/internal/v1/search"
BODY = {
    "tags": ["Farming Sim", "Relaxing"],
    "exclude_tags": ["Horror"],
    "description": "a relaxing farming game",
    "similar_to": "Stardew Valley",
    "limit": 2,
}


@pytest.fixture
def searcher():
    return FakeSearcher(
        [SearchItem(11, 3.91234567), SearchItem(22, 2.5), SearchItem(33, 0.1)],
        ignored_tags=["Super Hard"],
        similar_to_app_id=413150,
    )


@pytest.fixture
def client(searcher):
    # lifespan(실제 모델 로딩)을 돌리지 않도록 with 없이 쓰고, 검색기만 가짜로 갈아 끼운다
    app = create_app(make_test_settings())
    app.dependency_overrides[get_searcher] = lambda: searcher
    return TestClient(app)


def test_returns_ranked_items_with_ignored_tags(client):
    response = client.post(URL, json=BODY)

    assert response.status_code == 200
    assert response.json() == {
        "items": [{"app_id": 11, "score": 3.9123}, {"app_id": 22, "score": 2.5}],
        "ignored_tags": ["Super Hard"],
        "similar_to_app_id": 413150,
    }


def test_request_is_passed_to_searcher_as_domain_values(client, searcher):
    client.post(URL, json=BODY)

    keywords = SearchKeywords(["Farming Sim", "Relaxing"], ["Horror"], "a relaxing farming game", "Stardew Valley")
    assert searcher.calls == [(keywords, 2)]


def test_optional_fields_have_defaults(client, searcher):
    client.post(URL, json={"description": "a zombie survival game"})

    assert searcher.calls[-1] == (SearchKeywords([], [], "a zombie survival game", ""), 10)


def test_no_usable_keywords_is_422(client):
    response = client.post(URL, json={"exclude_tags": ["Horror"]})

    assert response.status_code == 422
    assert response.json()["code"] == "NO_SEARCH_KEYWORDS"


@pytest.mark.parametrize(
    "body",
    [
        {"description": "x", "limit": 0},
        {"description": "x", "limit": 51},
        {"description": "x" * 501},
        {"tags": ["t"] * 11},
        {"description": "x", "tags": "Farming Sim"},
    ],
)
def test_invalid_requests_are_400_validation_error(client, body):
    response = client.post(URL, json=body)

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_search_is_503_when_the_server_started_without_search_files():
    app = create_app(make_test_settings())  # lifespan을 돌리지 않았으므로 app.state.searcher가 없다

    response = TestClient(app).post(URL, json=BODY)

    assert response.status_code == 503
    assert response.json()["code"] == "SEARCH_UNAVAILABLE"

import numpy as np
import pytest

from app.infra.search_index import SearchIndex

# 3차원 벡터로 만든 작은 게임 6개. 벡터 방향이 곧 "내용"이다 (x = 농사, y = 공포, z = 우주)
GAMES = [  # (app_id, 이름, 태그, 리뷰 수, 벡터)
    (1, "Farm Valley", ["Farming", "Cozy"], 1000, [1.0, 0.0, 0.0]),
    (2, "Farm Valley 2", ["Farming"], 100, [0.9, 0.1, 0.0]),
    (3, "Dark Manor", ["Horror"], 5000, [0.0, 1.0, 0.0]),
    (4, "Cozy Haunt", ["Horror", "Cozy"], 200, [0.1, 0.9, 0.0]),
    (5, "Star Fields", ["Space"], 300, [0.0, 0.0, 1.0]),
    (6, "Horror Farm", ["Farming", "Horror"], 50, [0.8, 0.0, 0.2]),
]
TAG_IDF = {"Farming": 2.0, "Cozy": 3.0, "Horror": 1.5, "Space": 4.0}
FARM = np.array([1.0, 0.0, 0.0])


@pytest.fixture
def index():
    emb = np.array([g[4] for g in GAMES], dtype=np.float16)
    return SearchIndex(emb, [g[0] for g in GAMES], [g[1] for g in GAMES], [g[2] for g in GAMES],
                       [g[3] for g in GAMES], TAG_IDF)


def app_ids(result):
    return [app_id for app_id, _ in result]


def test_resolve_tags_ignores_case_and_reports_unknown_tags(index):
    valid, ignored = index.resolve_tags(["farming", "COZY", "Super Hard", "Farming"])

    assert valid == ["Farming", "Cozy"]
    assert ignored == ["Super Hard"]


def test_find_game_prefers_exact_name_then_most_reviewed_partial_match(index):
    assert index.find_game("farm valley") == 0  # 정확히 같은 이름이 있으면 그것
    assert index.find_game("Farm") == 0  # 부분 일치만 있으면 리뷰가 가장 많은 게임 (Dark Manor는 'farm'이 없다)
    assert index.find_game("Nothing Like This") is None
    assert index.find_game("  ") is None


def test_similar_content_ranks_first(index):
    result = index.search(FARM, [], [], limit=6)

    assert app_ids(result)[:2] == [1, 2]  # 내용이 가장 비슷한 두 게임
    assert app_ids(result).index(6) < app_ids(result).index(5)  # 우주 게임보다 농사에 가까운 게임이 앞


def test_tags_boost_games_that_have_them(index):
    # 질의는 공포 쪽이지만 Space 태그를 요청하면 태그를 가진 게임(Star Fields)의 순위가 올라간다
    horror = np.array([0.0, 1.0, 0.0])
    plain = app_ids(index.search(horror, [], [], limit=6))
    boosted = app_ids(index.search(horror, ["Space"], [], limit=6))

    assert boosted.index(5) < plain.index(5)


def test_exclude_tags_remove_games(index):
    result = index.search(FARM, [], ["Horror"], limit=6)

    assert set(app_ids(result)).isdisjoint({3, 4, 6})


def test_exclude_row_removes_the_game_itself(index):
    result = index.search(FARM, [], [], limit=6, exclude_row=0)

    assert 1 not in app_ids(result)


def test_limit_is_respected_and_empty_when_everything_is_excluded(index):
    assert len(index.search(FARM, [], [], limit=2)) == 2
    assert index.search(FARM, [], ["Farming", "Horror", "Space"], limit=5) == []


def test_scores_are_sorted_descending(index):
    scores = [score for _, score in index.search(FARM, ["Farming"], [], limit=6)]

    assert scores == sorted(scores, reverse=True)

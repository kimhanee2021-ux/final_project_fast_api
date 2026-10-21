"""저장된 실제 모델 파일로 돌리는 통합 테스트. 모델 폴더가 없으면 건너뛴다 (로딩에 수 초 걸린다)."""
import pytest

from app.domain.recommender import NoKnownGamesError, OwnedGame
from tests.support import make_test_settings

MODEL_DIR = make_test_settings().model_dir

# TWO_TOWER_API.md 예시에 쓰인, 모델이 아는 게임들
HISTORY = [OwnedGame(292030, 200), OwnedGame(489830, 350), OwnedGame(1245620, 180)]

pytestmark = pytest.mark.skipif(
    not (MODEL_DIR / "user_tower.keras").exists(), reason="모델 파일 없음"
)


@pytest.fixture(scope="module")
def recommender():
    from app.infrastructure.two_tower import TwoTowerRecommender

    return TwoTowerRecommender(MODEL_DIR)


def test_returns_requested_number_of_ranked_items(recommender):
    result = recommender.recommend(HISTORY, exclude_app_ids=set(), limit=10)

    scores = [i.score for i in result.items]
    assert len(result.items) == 10
    assert scores == sorted(scores, reverse=True)
    assert len({i.app_id for i in result.items}) == 10


def test_never_recommends_owned_or_excluded_games(recommender):
    first = recommender.recommend(HISTORY, exclude_app_ids=set(), limit=10)
    excluded = {first.items[0].app_id, first.items[1].app_id}
    owned = {g.app_id for g in HISTORY}

    result = recommender.recommend(HISTORY, exclude_app_ids=excluded, limit=10)

    recommended = {i.app_id for i in result.items}
    assert not recommended & owned
    assert not recommended & excluded


def test_same_input_gives_same_output(recommender):
    a = recommender.recommend(HISTORY, set(), 5)
    b = recommender.recommend(HISTORY, set(), 5)

    assert [i.app_id for i in a.items] == [i.app_id for i in b.items]


def test_unknown_games_are_ignored_but_known_ones_still_used(recommender):
    result = recommender.recommend([*HISTORY, OwnedGame(-1, 10)], set(), 5)

    assert result.ignored_app_ids == [-1]
    assert result.used_app_ids == sorted(g.app_id for g in HISTORY)


def test_only_unknown_games_raises(recommender):
    with pytest.raises(NoKnownGamesError):
        recommender.recommend([OwnedGame(-1, 10)], set(), 5)


def test_only_last_hist_len_games_are_used(recommender):
    many = [OwnedGame(app_id, 1.0) for app_id in recommender._games.entity_app_ids[:80]]

    result = recommender.recommend(many, set(), 5)

    assert len(result.used_app_ids) == recommender.hist_len

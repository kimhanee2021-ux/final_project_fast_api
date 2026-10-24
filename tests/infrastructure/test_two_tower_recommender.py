"""저장된 실제 모델 파일로 돌리는 통합 테스트. 모델 폴더가 없으면 건너뛴다 (로딩에 수 초 걸린다)."""
import numpy as np
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
    from app.infra.two_tower import TwoTowerRecommender

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


# ---- 신작 칸 (game_vecs_content.npy, gid_of_row.npy 가 있을 때만) ----
@pytest.fixture(scope="module")
def has_new_slots(recommender):
    return recommender._games.has_new_slots


def test_new_slots_fill_requested_count_and_mark_source(recommender, has_new_slots):
    if not has_new_slots:
        pytest.skip("신작 칸 파일 없음")
    result = recommender.recommend(HISTORY, set(), 10, new_slots=3)

    sources = [i.source for i in result.items]
    assert len(result.items) == 10
    assert sources == ["main"] * 7 + ["new"] * 3
    assert len({i.app_id for i in result.items}) == 10


def test_new_slot_games_are_not_in_training_set_and_main_slots_are(recommender, has_new_slots):
    if not has_new_slots:
        pytest.skip("신작 칸 파일 없음")
    games = recommender._games
    result = recommender.recommend(HISTORY, set(), 10, new_slots=4)

    for item in result.items:
        is_new = bool(games._is_new[games.row_of(item.app_id) - 1])
        assert is_new == (item.source == "new")


def test_new_slots_never_exceed_limit_and_default_is_unchanged(recommender, has_new_slots):
    if not has_new_slots:
        pytest.skip("신작 칸 파일 없음")
    all_new = recommender.recommend(HISTORY, set(), 5, new_slots=99)
    default = recommender.recommend(HISTORY, set(), 5)
    again = recommender.recommend(HISTORY, set(), 5, new_slots=0)

    assert [i.source for i in all_new.items] == ["new"] * 5
    assert [i.app_id for i in default.items] == [i.app_id for i in again.items]
    assert {i.source for i in default.items} == {"main"}


def test_new_slots_respect_excluded_games(recommender, has_new_slots):
    if not has_new_slots:
        pytest.skip("신작 칸 파일 없음")
    first = recommender.recommend(HISTORY, set(), 10, new_slots=3)
    excluded = {i.app_id for i in first.items if i.source == "new"}

    second = recommender.recommend(HISTORY, excluded, 10, new_slots=3)

    assert not {i.app_id for i in second.items} & excluded


def test_candidate_mask_removes_games_from_results(recommender):
    games = recommender._games
    top = recommender.recommend(HISTORY, set(), 10)
    banned_app = top.items[0].app_id
    allowed_before = games._allowed
    mask = np.ones(len(games.entity_app_ids), dtype=bool)
    mask[games.row_of(banned_app) - 1] = False
    games._allowed = mask
    try:
        result = recommender.recommend(HISTORY, set(), 10)
    finally:
        games._allowed = allowed_before

    assert banned_app not in {i.app_id for i in result.items}

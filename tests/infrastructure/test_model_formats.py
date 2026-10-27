"""어텐션 모델 파일을 읽는지와, 같은 게임이 중복으로 올 때의 처리를 확인한다.
모델 폴더가 없으면 테스트는 건너뛴다 (로딩에 수 초 걸린다)."""
import numpy as np
import pytest

from app.domain.recommender import OwnedGame
from tests.support import make_test_settings

ATTENTION_DIR = make_test_settings().model_dir

HISTORY = [OwnedGame(292030, 200), OwnedGame(489830, 350), OwnedGame(1245620, 180)]


def load(model_dir):
    if not (model_dir / "user_tower.keras").exists():
        pytest.skip(f"모델 파일 없음: {model_dir}")
    from app.infra.two_tower import TwoTowerRecommender

    return TwoTowerRecommender(model_dir)


@pytest.fixture(scope="module")
def attention():
    return load(ATTENTION_DIR)


def test_recommends_without_game_ids(attention):
    result = attention.recommend(HISTORY, set(), 10)

    assert len({i.app_id for i in result.items}) == 10


def test_new_slots_come_last_and_are_marked(attention):
    result = attention.recommend(HISTORY, set(), 10, new_slots=3)

    assert [i.source for i in result.items] == ["main"] * 7 + ["new"] * 3


def test_a_game_sent_twice_counts_once_using_its_last_playtime(attention):
    twice = attention.recommend([OwnedGame(292030, 10), OwnedGame(489830, 350), OwnedGame(292030, 200)], set(), 10)
    once = attention.recommend([OwnedGame(489830, 350), OwnedGame(292030, 200)], set(), 10)

    assert [i.app_id for i in twice.items] == [i.app_id for i in once.items]
    assert twice.used_app_ids == once.used_app_ids == [292030, 489830]


def test_unknown_game_sent_twice_is_reported_once(attention):
    result = attention.recommend([*HISTORY, OwnedGame(-1, 10), OwnedGame(-1, 20)], set(), 5)

    assert result.ignored_app_ids == [-1]


def test_service_candidate_mask_is_narrower_than_the_exported_one(attention):
    exported_path = ATTENTION_DIR / "candidate_mask_exported.npy"
    if not exported_path.exists():
        pytest.skip("candidate_mask_exported.npy 없음")
    exported = np.load(exported_path)
    service = attention._games._allowed

    assert service.sum() < exported.sum()
    assert not (service & ~exported).any()  # 서비스 마스크가 허용한 게임은 모두 내보낸 마스크도 허용한 것

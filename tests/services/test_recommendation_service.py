import pytest

from app.domain.recommender import NoKnownGamesError, OwnedGame, Recommendation
from app.domain.repositories import GameSummary, UserNotFoundError
from app.services.recommendation_service import RecommendationService
from tests.fakes import (
    FakeGameCatalogRepository,
    FakeLibraryRepository,
    FakeRecommender,
    FakeUserRepository,
)

USER_ID = 7
PLAYED = OwnedGame(app_id=100, playtime_hours=12.5)
OTHER_PLAYED = OwnedGame(app_id=200, playtime_hours=0.5)
UNPLAYED = OwnedGame(app_id=300, playtime_hours=0)


def build_service(library: list[OwnedGame], recommendations: list[Recommendation], catalog=()):
    recommender = FakeRecommender(recommendations)
    service = RecommendationService(
        recommender=recommender,
        users=FakeUserRepository({USER_ID}),
        library=FakeLibraryRepository({USER_ID: library}),
        catalog=FakeGameCatalogRepository(list(catalog)),
    )
    return service, recommender


def test_unplayed_games_are_not_used_as_taste_history():
    service, recommender = build_service([PLAYED, UNPLAYED, OTHER_PLAYED], [Recommendation(1, 0.9)])

    service.recommend_for_user(USER_ID, limit=5)

    history, _, _ = recommender.calls[0]
    assert history == [PLAYED, OTHER_PLAYED]


def test_unplayed_games_are_still_excluded_from_recommendations():
    service, recommender = build_service([PLAYED, UNPLAYED], [Recommendation(1, 0.9)])

    service.recommend_for_user(USER_ID, limit=5)

    _, exclude_app_ids, _ = recommender.calls[0]
    assert exclude_app_ids == {PLAYED.app_id, UNPLAYED.app_id}


def test_history_keeps_library_order():
    older, newer = OwnedGame(1, 10), OwnedGame(2, 20)
    service, recommender = build_service([older, newer], [Recommendation(9, 0.1)])

    service.recommend_for_user(USER_ID, limit=5)

    assert recommender.calls[0][0] == [older, newer]


def test_limit_is_passed_to_recommender():
    service, recommender = build_service([PLAYED], [Recommendation(1, 0.9)])

    service.recommend_for_user(USER_ID, limit=3)

    assert recommender.calls[0][2] == 3


def test_ranks_start_at_one_and_follow_recommender_order():
    recs = [Recommendation(11, 0.9), Recommendation(22, 0.5), Recommendation(33, 0.1)]
    service, _ = build_service([PLAYED], recs)

    result = service.recommend_for_user(USER_ID, limit=10)

    assert [(d.rank, d.recommendation.app_id) for d in result.items] == [(1, 11), (2, 22), (3, 33)]


def test_game_info_is_attached_and_missing_catalog_entry_is_none():
    known = GameSummary(11, "Known Game", "RPG", "http://img/11.jpg")
    service, _ = build_service(
        [PLAYED], [Recommendation(11, 0.9), Recommendation(22, 0.5)], catalog=[known]
    )

    result = service.recommend_for_user(USER_ID, limit=10)

    assert result.items[0].game == known
    assert result.items[1].game is None


def test_meta_counts_used_and_unplayed_games():
    service, _ = build_service([PLAYED, OTHER_PLAYED, UNPLAYED], [Recommendation(1, 0.9)])

    result = service.recommend_for_user(USER_ID, limit=5)

    assert result.used_game_count == 2
    assert result.unplayed_game_count == 1


def test_unknown_user_raises_before_touching_library():
    service, recommender = build_service([PLAYED], [Recommendation(1, 0.9)])

    with pytest.raises(UserNotFoundError):
        service.recommend_for_user(user_id=999, limit=5)

    assert recommender.calls == []
    assert service._library.requested_user_ids == []


def test_library_with_only_unplayed_games_cannot_be_recommended():
    service, _ = build_service([UNPLAYED], [Recommendation(1, 0.9)])

    with pytest.raises(NoKnownGamesError):
        service.recommend_for_user(USER_ID, limit=5)


def test_empty_library_cannot_be_recommended():
    service, _ = build_service([], [Recommendation(1, 0.9)])

    with pytest.raises(NoKnownGamesError):
        service.recommend_for_user(USER_ID, limit=5)

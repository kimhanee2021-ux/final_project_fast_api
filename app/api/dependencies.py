from fastapi import Request

from app.domain.recommender import Recommender
from app.domain.searcher import SearchUnavailableError, Searcher


def get_recommender(request: Request) -> Recommender:
    return request.app.state.recommender


def get_searcher(request: Request) -> Searcher:
    searcher = getattr(request.app.state, "searcher", None)
    if searcher is None:
        raise SearchUnavailableError
    return searcher

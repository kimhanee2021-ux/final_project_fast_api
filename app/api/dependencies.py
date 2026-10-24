from fastapi import Request

from app.domain.recommender import Recommender


def get_recommender(request: Request) -> Recommender:
    return request.app.state.recommender

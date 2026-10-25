import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.v1 import health, recommendations, search
from app.core.config import Settings, get_settings
from app.infra.e5_searcher import E5Searcher
from app.infra.two_tower import TwoTowerRecommender

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.recommender = TwoTowerRecommender(app.state.settings.model_dir)  # 시작 시 한 번만 로드
    search_dir = app.state.settings.search_dir
    if search_dir.exists():
        app.state.searcher = E5Searcher(search_dir, app.state.settings.search_encoder)  # 추천기와 같이 한 번만 로드
    else:  # 검색 파일이 없어도 추천 서버는 정상 기동한다. 검색 API만 503
        logger.warning("검색 모델 폴더가 없어 검색 API를 끕니다: %s", search_dir)
        app.state.searcher = None
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """앱을 조립한다. 설정을 직접 넘기면 환경변수 없이도 만들 수 있다(테스트).

    Spring 백엔드만 호출하는 내부 서비스다. 외부에 노출하지 않는다.
    실행: uvicorn app.main:create_app --factory --port 8000
    """
    app = FastAPI(title="Game Recommendation Model API", version="2.0.0", lifespan=lifespan)
    app.state.settings = settings or get_settings()
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(recommendations.router, prefix="/internal/v1")
    app.include_router(search.router, prefix="/internal/v1")
    return app

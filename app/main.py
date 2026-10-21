from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.v1 import health, recommendations
from app.core.config import Settings, get_settings
from app.core.database import create_session_factory
from app.infrastructure.two_tower import TwoTowerRecommender


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.recommender = TwoTowerRecommender(app.state.settings.model_dir)  # 시작 시 한 번만 로드
    yield
    app.state.session_factory.kw["bind"].dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """앱을 조립한다. 설정을 직접 넘기면 환경변수 없이도 만들 수 있다(테스트).

    실행: uvicorn app.main:create_app --factory --port 8000
    """
    settings = settings or get_settings()
    app = FastAPI(title="Game Recommendation API", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = create_session_factory(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_base_url],
        allow_methods=["GET"],
        allow_headers=["Authorization"],
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(recommendations.router, prefix="/api/v1")
    return app

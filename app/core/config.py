from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_RECOMMENDATIONS = 10
MAX_RECOMMENDATIONS = 50
DEFAULT_SEARCH_RESULTS = 10
MAX_SEARCH_RESULTS = 50
MAX_SEARCH_KEYWORDS = 10  # 검색 요청 한 건에 담을 수 있는 태그 수 (tags, exclude_tags 각각)
MAX_HISTORY = 5000  # 요청 한 건에 담을 수 있는 플레이 이력/제외 목록의 최대 길이 (비정상적으로 큰 요청 차단)


class Settings(BaseSettings):
    # 어텐션 추천 모델 폴더 (user_tower.keras, game_vecs.npy 등)
    model_dir: Path = BASE_DIR / "saved_model_attention"
    search_dir: Path = BASE_DIR / "search_model"  # 없으면 검색 API만 꺼진 채로 시작한다
    search_encoder: str = "intfloat/multilingual-e5-base"  # 질의를 벡터로 바꾸는 모델 이름 또는 폴더 경로

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """실제 실행 때만 환경변수/.env에서 읽는다. import 시점에는 아무것도 읽지 않는다."""
    return Settings()

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_RECOMMENDATIONS = 10
MAX_RECOMMENDATIONS = 50
MAX_HISTORY = 5000  # 요청 한 건에 담을 수 있는 플레이 이력/제외 목록의 최대 길이 (비정상적으로 큰 요청 차단)


class Settings(BaseSettings):
    model_dir: Path = BASE_DIR / "saved_model_twotower" / "saved_model_twotower"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """실제 실행 때만 환경변수/.env에서 읽는다. import 시점에는 아무것도 읽지 않는다."""
    return Settings()

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_RECOMMENDATIONS = 10
MAX_RECOMMENDATIONS = 50
DEFAULT_NEW_SLOTS = 3  # 추천 중 신작 칸 수의 기본값 (0 = 신작 칸 없음). 후보 마스크(리뷰 100개 이상)와 함께 쓴다


class Settings(BaseSettings):
    """환경변수 이름은 Spring 백엔드(.env)와 같다. 같은 이름은 같은 값을 써야 한다."""

    # Spring과 동일: jdbc:mysql://host:3306/db?serverTimezone=... 형식 그대로 받는다
    db_url: str
    db_username: str
    db_password: str
    # 토큰 서명 검증용. Spring이 발급할 때 쓰는 값과 같아야 한다
    jwt_secret_key: str
    frontend_base_url: str = "http://localhost:5173"  # CORS 허용 프론트 주소

    model_dir: Path = BASE_DIR / "saved_model_twotower" / "saved_model_twotower"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    @property
    def database_url(self) -> URL:
        """JDBC URL을 SQLAlchemy(pymysql) 접속 정보로 바꾼다. serverTimezone 등 JDBC 전용 옵션은 쓰지 않는다."""
        parsed = urlparse(self.db_url.removeprefix("jdbc:"))
        return URL.create(
            "mysql+pymysql",
            username=self.db_username,
            password=self.db_password,
            host=parsed.hostname,
            port=parsed.port or 3306,
            database=parsed.path.lstrip("/"),
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    """실제 실행 때만 환경변수/.env에서 읽는다. import 시점에는 아무것도 읽지 않는다."""
    return Settings()

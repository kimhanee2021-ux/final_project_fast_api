from app.core.config import Settings


def make_test_settings() -> Settings:
    """개발자의 .env/OS 환경변수와 무관한 테스트 설정. 생성자 인자가 환경변수보다 우선하고 .env는 읽지 않는다."""
    return Settings(_env_file=None)

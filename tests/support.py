from app.core.config import Settings

TEST_JWT_SECRET = "test-secret-key-test-secret-key-test-secret-key-0123456789"


def make_test_settings() -> Settings:
    """개발자의 .env/OS 환경변수와 무관한 테스트 설정. 생성자 인자가 환경변수보다 우선하고 .env는 읽지 않는다."""
    return Settings(
        _env_file=None,
        db_url="jdbc:mysql://localhost:3306/test_db",
        db_username="test",
        db_password="test",
        jwt_secret_key=TEST_JWT_SECRET,
        frontend_base_url="http://localhost:5173",
    )

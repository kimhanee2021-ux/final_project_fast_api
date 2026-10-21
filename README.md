# Game Recommendation API

로그인한 사용자의 보유 게임(플레이한 게임만)으로 Two-Tower 모델이 게임을 추천하는 FastAPI 서비스.
Spring 백엔드의 DB(MySQL)를 직접 읽고, Spring이 발급한 JWT로 사용자를 식별한다.

## 실행

```
conda env create -f environment.yml
conda activate final-project-fast-api
copy .env.example .env      # 값 채우기 (Spring .env와 같은 값)
uvicorn app.main:create_app --factory --port 8000
```

`environment.yml`은 프로젝트 루트에서 실행해야 한다 (`requirements-dev.txt`를 상대 경로로 읽음).
conda 없이 쓰려면 `python -m venv .venv` 후 `pip install -r requirements-dev.txt`.

- 문서: http://localhost:8000/docs
- 모델 파일은 `saved_model_twotower/saved_model_twotower/`에 있어야 한다. 서버 시작 시 한 번 로딩한다.

## 환경변수 (`.env`)

Spring 백엔드의 `.env`와 같은 이름을 쓴다. OS 환경변수가 있으면 `.env`보다 우선한다.

| 키 | 설명 |
|---|---|
| `DB_URL` | Spring과 같은 JDBC URL (`jdbc:mysql://host:3306/db`) |
| `DB_USERNAME`, `DB_PASSWORD` | DB 계정 |
| `JWT_SECRET_KEY` | Spring과 같은 서명 키 (HS256/384/512) |
| `FRONTEND_BASE_URL` | CORS 허용 오리진 (기본 `http://localhost:5173`) |

## API

### `GET /api/v1/users/me/recommendations?limit=10`

`Authorization: Bearer <Spring이 발급한 JWT>` 필요. `limit`은 1~50 (기본 10).
추천 대상은 토큰의 사용자 본인뿐이며 user_id를 쿼리로 넘길 수 없다.

```json
{
  "recommendations": [
    {"rank": 1, "app_id": 374320, "score": 0.9123,
     "game": {"name": "DARK SOULS III", "genre": "...", "thumbnail_url": "..."}}
  ],
  "meta": {"used_game_count": 12, "unplayed_game_count": 3}
}
```

`score`는 요청 안에서 순위를 매기는 용도이며 확률이 아니다.
`game`은 `games` 테이블에 없는 게임이면 `null`.

### `GET /health` → `{"status": "ok"}`

### 오류 형식 (Spring `ErrorResponse`와 동일: `{"code", "error"}`)

| 상태 | code | 의미 |
|---|---|---|
| 401 | `UNAUTHENTICATED` | 토큰이 없거나 유효하지 않음 |
| 404 | `USER_NOT_FOUND` | 토큰은 유효하나 회원이 없음 |
| 409 | `NO_PLAYED_GAMES` | 추천에 쓸 플레이한 게임이 없음 |
| 400 | `VALIDATION_ERROR` | 잘못된 쿼리 (예: `limit=0`) |
| 500 | `INTERNAL_ERROR` | 서버 오류 |

## 추천 방식

1. `library_games`에서 사용자의 보유 게임을 읽는다.
2. 플레이 시간이 0인 게임은 취향 계산에서 제외하고, 이미 보유한 게임은 추천에서 제외한다.
3. 최근 50개 게임을 `1 + log(1 + 시간)` 가중치로 유저 타워에 넣어 사용자 벡터를 만든다.
4. 미리 계산된 게임 벡터(`game_vecs.npy`)와 내적해 상위 N개를 고른다.

모델이 모르는 게임은 취향 계산에서 무시된다.

## 구조

```
app/
  api/             라우터, 인증 의존성, 오류 핸들러
  schemas/         요청/응답 모델 (응답 변환 포함)
  services/        추천 유스케이스 (프레임워크 비의존)
  domain/          Protocol 인터페이스와 도메인 타입
  infrastructure/  Two-Tower 모델, MySQL 저장소, JWT 검증
  core/            설정, DB 세션
```

서비스는 `domain`의 인터페이스에만 의존하고, 구현체(모델, DB, JWT)는 `api/dependencies.py`에서 조립한다.

## 테스트

```
pytest
```

가짜 저장소/추천기로 API와 서비스를 검증하고, 실제 모델 파일이 있으면 모델 통합 테스트도 돌린다 (모델 로딩에 수 초).

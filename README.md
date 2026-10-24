# Game Recommendation Model API

Two-Tower 모델로 게임을 추천하는 **내부 추론 서버**. Spring 백엔드만 호출하며 외부(프론트)에 노출하지 않는다.
DB 접근, 인증, 캐싱, 추천 목록 저장은 모두 Spring이 맡고, 이 서버는 받은 플레이 이력으로 순위만 계산한다.

```
front → Spring Boot → DB
            ↓ POST /internal/v1/recommendations
         FastAPI (모델 추론)
```

## 실행

```
conda env create -f environment.yml
conda activate final-project-fast-api
uvicorn app.main:create_app --factory --port 8000
```

`environment.yml`은 프로젝트 루트에서 실행해야 한다 (`requirements-dev.txt`를 상대 경로로 읽음).
conda 없이 쓰려면 `python -m venv .venv` 후 `pip install -r requirements-dev.txt`.

- 문서: http://localhost:8000/docs
- 모델 파일은 `saved_model_twotower/saved_model_twotower/`에 있어야 한다. 서버 시작 시 한 번 로딩한다.
- 환경변수는 `MODEL_DIR`(모델 폴더 변경) 하나뿐이다. `.env.example` 참고.
- 인증이 없으므로 localhost/내부망에서만 열고 Spring만 접근하게 한다.

## API

### `POST /internal/v1/recommendations`

```json
{
  "played_games": [{"app_id": 292030, "playtime_hours": 200.5}],
  "exclude_app_ids": [292030, 440],
  "limit": 10,
  "new_slots": 3
}
```

| 필드 | 설명 |
|---|---|
| `played_games` | 플레이한 게임. **오래된 순 → 최근 순**. 모델은 최근 이력부터 사용 |
| `exclude_app_ids` | 추천에서 뺄 게임. 미플레이 포함 보유 게임 전체를 넘긴다 (기본 `[]`) |
| `limit` | 1~50 (기본 10) |
| `new_slots` | `limit` 중 신작(학습에 없던 게임) 칸 수. 0~50 (기본 0) |

```json
{
  "items": [{"app_id": 374320, "score": 0.9123, "source": "main"}],
  "used_app_ids": [292030],
  "ignored_app_ids": []
}
```

- `items`는 점수가 높은 순이다. `score`는 요청 안에서 순위를 매기는 용도이며 확률이 아니다.
- `source`: `main` 기본 추천, `new` 신작 칸.
- `used_app_ids`: 취향 계산에 쓴 게임, `ignored_app_ids`: 모델이 몰라서 뺀 게임.
- 게임 이름/장르/썸네일은 주지 않는다. `app_id`로 Spring이 붙인다.

### `GET /health` → `{"status": "ok"}`

### 오류 형식 `{"code", "error"}`

| 상태 | code | 의미 |
|---|---|---|
| 400 | `VALIDATION_ERROR` | 잘못된 요청 본문 |
| 422 | `NO_KNOWN_GAMES` | 이력에 모델이 아는 게임이 없음 (Spring이 사용자용 409 등으로 변환) |
| 500 | `INTERNAL_ERROR` | 서버 오류 |

## 추천 방식

1. 최근 50개(`hist_len`) 게임을 `1 + log(1 + 시간)` 가중치로 유저 타워에 넣어 사용자 벡터를 만든다.
2. 미리 계산된 게임 벡터(`game_vecs.npy`)와 내적해 상위 N개를 고른다. `exclude_app_ids`와 이력에 쓴 게임은 제외한다.
3. 신작 칸이 있으면 학습에 없던 게임은 콘텐츠 벡터로 따로 점수를 내어 정해진 칸 수만큼 채운다.

모델이 모르는 게임은 취향 계산에서 무시된다.

## 구조

```
app/
  api/       라우터, 오류 핸들러, 의존성
  schemas/   요청/응답 모델 (도메인 변환 포함)
  domain/    Recommender 인터페이스와 도메인 타입
  infra/     Two-Tower 모델 (유저 인코더, 게임 인덱스)
  core/      설정
```

라우터는 `domain.Recommender` 인터페이스에만 의존하고, 구현체(`TwoTowerRecommender`)는 `main.py`의 lifespan에서 한 번 만들어 `api/dependencies.py`로 주입한다.

## 테스트

```
pytest
```

가짜 추천기로 API를 검증하고, 실제 모델 파일이 있으면 모델 통합 테스트도 돌린다 (모델 로딩에 수 초).

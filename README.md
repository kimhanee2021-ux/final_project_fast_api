# Game Recommendation Model API

Two-Tower 모델(유저 타워에 어텐션을 쓴 모델)로 게임을 추천하는 **내부 추론 서버**. Spring 백엔드만 호출하며 외부(프론트)에 노출하지 않는다.
DB 접근, 인증, 캐싱, 추천 목록 저장은 모두 Spring이 맡고, 이 서버는 받은 플레이 이력으로 순위만 계산한다.

```
front → Spring Boot → DB
            ↓ POST /internal/v1/recommendations   (플레이 이력 → 추천)
         ↓ POST /internal/v1/search            (LLM이 뽑은 키워드 → 검색)
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
- 추천 모델 파일은 기본으로 `saved_model_attention/`에 있어야 한다. 서버 시작 시 한 번 로딩한다.
- 검색 파일은 `search_model/`에 있어야 한다 (아래 "검색" 참고). 없으면 검색 API만 503이고 추천은 정상 동작한다.
- 환경변수는 모두 선택이다: `MODEL_DIR`(추천 모델 폴더, 기본 `saved_model_attention`), `SEARCH_DIR`(검색 파일 폴더), `SEARCH_ENCODER`(질의 인코더). `.env.example` 참고.
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

### `POST /internal/v1/search`

Spring이 사용자의 한국어 검색어를 LLM(Gemini 등)으로 **영어 키워드**로 바꿔 보내면, 어울리는 게임의 `app_id`를 순서대로 돌려준다.

```json
{
  "tags": ["Farming Sim", "Relaxing"],
  "exclude_tags": ["Horror"],
  "description": "a relaxing and cozy farming game",
  "similar_to": "Stardew Valley",
  "limit": 10
}
```

| 필드 | 설명 |
|---|---|
| `tags` | 원하는 Steam 태그(영어, 최대 10개). 가진 게임에 가산점. 대소문자는 구분하지 않고, 없는 태그는 무시 |
| `exclude_tags` | 이 태그를 가진 게임은 결과에서 뺀다 (최대 10개) |
| `description` | 원하는 게임을 설명하는 영어 한 문장 (최대 500자). 의미가 비슷한 게임을 찾는 데 쓴다 |
| `similar_to` | "OO 같은 게임"일 때 그 게임의 영어 이름. 그 게임 자신은 결과에서 빠진다 |
| `limit` | 1~50 (기본 10) |

`tags`, `description`, `similar_to` 중 하나는 있어야 한다. 전부 선택이지만 `description`을 함께 주는 편이 결과가 좋다.

```json
{
  "items": [{"app_id": 413150, "score": 3.9123}],
  "ignored_tags": ["Super Hard"],
  "similar_to_app_id": 413150
}
```

- `items`는 점수가 높은 순이다. `score`는 요청 안에서 순위를 매기는 용도이며 확률이 아니다.
- `ignored_tags`: 데이터에 없어서 무시한 태그. 비어 있지 않으면 LLM이 목록에 없는 태그를 지어낸 것이다.
- `similar_to_app_id`: `similar_to`로 찾은 게임. 요청에 없거나 못 찾았으면 `null`.
- 이름/이미지는 주지 않는다. `app_id`로 Spring이 붙인다. 검색 대상은 리뷰 100개 이상, 이름 중복·Demo·Playtest 제외 게임 약 2.2만 개다.

### `GET /health` → `{"status": "ok"}`

### 오류 형식 `{"code", "error"}`

| 상태 | code | 의미 |
|---|---|---|
| 400 | `VALIDATION_ERROR` | 잘못된 요청 본문 |
| 422 | `NO_KNOWN_GAMES` | 이력에 모델이 아는 게임이 없음 (Spring이 사용자용 409 등으로 변환) |
| 422 | `NO_SEARCH_KEYWORDS` | 검색에 쓸 태그/설명/비슷한 게임이 하나도 없음 |
| 503 | `SEARCH_UNAVAILABLE` | `search_model/`이 없어 검색을 쓸 수 없음 |
| 500 | `INTERNAL_ERROR` | 서버 오류 |

## 추천 방식

1. 같은 게임이 여러 번 오면 마지막 것만 쓴다. 최근 50개(`hist_len`) 게임을 `1 + log(1 + 시간)` 가중치로 유저 타워에 넣어 사용자 벡터를 만든다.
   - 어텐션 모델의 유저 타워는 보유 게임끼리 서로 참고(어텐션)한 뒤 플레이시간 가중합으로 사용자 벡터를 만든다. 게임 ID는 입력으로 쓰지 않는다.
2. 미리 계산된 게임 벡터(`game_vecs.npy`)와 내적해 상위 N개를 고른다. `exclude_app_ids`와 이력에 쓴 게임은 제외하고, 후보 마스크(`candidate_mask.npy`)가 허용한 게임만 후보가 된다.
3. 신작 칸이 있으면 학습에 없던 게임(`in_train.npy`가 False인 게임) 중에서 정해진 칸 수만큼 채운다. 어텐션 모델은 신작도 과거작과 같은 게임 벡터로 점수를 낸다.

모델이 모르는 게임은 취향 계산에서 무시된다.

### 모델 파일

`saved_model_attention/` (git에는 올리지 않는다. `.gitignore`)

| 파일 | 내용 |
|---|---|
| `user_tower.keras` | 유저 타워 (게임 타워 포함). 보유 게임 → 유저 벡터 |
| `game_vecs.npy` | 모든 게임(135,649개)의 벡터를 미리 계산한 표 |
| `entity_app_ids.npy` | `game_vecs`의 j번째 줄이 어느 AppID 게임인지 |
| `candidate_mask.npy` | **서비스가 쓰는 추천 후보.** 아래 규칙의 교집합 (약 22,070개) |
| `candidate_mask_exported.npy` | 학습 노트북이 내보낸 원본 마스크 (비게임 프로그램과 이름 중복만 제외, 약 131,615개). 서비스는 쓰지 않고 보관용 |
| `in_train.npy` | 학습 기록에 있던 게임인가 (False = 신작 등). 신작 칸에 사용 |
| `meta.json` | 모델 정보 (`hist_len`, 학습 시각, 검증·테스트 점수 등) |
| `reference_recommendations.json` | 학습 노트북이 계산한 예시 유저의 정답 추천 (서비스는 읽지 않음) |

**후보 마스크 규칙** (`candidate_mask.npy`): 이전 서비스 마스크(이름이 같으면 리뷰 최다 1개만, Demo/Playtest/Test Server/Dedicated Server 제외, **리뷰 100개 미만 제외**)와 어텐션 모델 마스크(게임이 아닌 프로그램 제외)의 **교집합**이다. 리뷰가 거의 없는 게임이 상위에 오르는 것을 막으면서, 이전 마스크가 거르지 못한 Wallpaper Engine 같은 프로그램도 뺀다. 원본 마스크만 쓰고 싶으면 `candidate_mask_exported.npy`를 `candidate_mask.npy`로 바꿔 넣는다.

## 검색 방식

1. `description`(과 `similar_to` 게임의 벡터)을 `intfloat/multilingual-e5-base`로 질의 벡터 하나로 만든다. 둘 다 없으면 태그 이름을 이어 붙여 쓴다.
2. 검색 대상 게임의 미리 계산된 벡터(`search_model/emb.npy`)와 내적해 유사도를 구하고, `exclude_tags`를 가진 게임은 뺀다.
3. `유사도 + 0.7 × 인기도(log 리뷰 수) + 3.0 × 태그 일치(0~1)`로 순위를 매긴다 (모두 후보 안에서 표준화). 태그 일치는 드문 태그에 더 큰 비중을 둔다.

한국어를 영어 키워드로 바꾸는 일은 이 서버가 아니라 호출하는 쪽(LLM)이 한다. 질의 인코더(약 1.1GB)는 처음 실행할 때 Hugging Face에서 내려받는다. 인터넷이 없는 곳에서는 미리 받아 둔 폴더 경로를 `SEARCH_ENCODER`에 지정한다.

`search_model/`은 용량 때문에 git에 올리지 않는다. 학습 저장소의 `training_bundle/nl_search/export_search_assets.py`가 만든다 (`emb.npy` 약 34MB, `games.json`, `tag_idf.json`, `meta.json`). 게임 데이터를 갱신하면 다시 만들어서 교체한다.

## 구조

```
app/
  api/       라우터, 오류 핸들러, 의존성
  schemas/   요청/응답 모델 (도메인 변환 포함)
  domain/    Recommender, Searcher 인터페이스와 도메인 타입
  infra/     Two-Tower 모델 (유저 인코더, 게임 인덱스), 검색 (질의 인코더, 검색 인덱스)
  core/      설정
```

라우터는 `domain.Recommender`/`domain.Searcher` 인터페이스에만 의존하고, 구현체(`TwoTowerRecommender`, `E5Searcher`)는 `main.py`의 lifespan에서 한 번 만들어 `api/dependencies.py`로 주입한다.

## 테스트

```
pytest
```

가짜 추천기/검색기로 API를 검증하고, 검색 점수 계산(`SearchIndex`)은 작은 가짜 데이터로 검증하며, 실제 모델 파일이 있으면 모델 통합 테스트도 돌린다 (모델 로딩에 수 초).

# DEVELOP.md

Ding-Dong11-BE 프로젝트 아키텍처 · 기술 스택 문서. **코드를 작성할 때 이 문서의 레이어 경계와 디렉토리 구조를 따른다** (CLAUDE.md 참조). DB 구조는 `database.md`를 참고한다.

## 기술 스택

| 기술 | 역할 |
|---|---|
| **uv** | 패키지 · 의존성 · 가상환경(venv) 관리. `uv sync` / `uv run` |
| **venv** | uv가 관리하는 격리 가상환경 |
| **FastAPI** | ASGI 웹 프레임워크 (API 레이어) |
| **uvicorn** | ASGI 서버. `uv run uvicorn app.main:app --reload` |
| **SQLAlchemy** | ORM (Model · Repository 레이어). 2.0 스타일 권장 |
| **Alembic** | DB 스키마 마이그레이션 (`database.md` 기준으로 버전 관리) |
| **PostgreSQL** | 주 RDBMS |
| **PostGIS + GiST** | 지도 좌표 공간 타입/인덱스. `geometry(Point, 4326)` + GiST 인덱스로 지도·거리 질의 |
| **Redis** | refresh token, 이메일 인증코드, 캐시 등 휘발성 데이터 |
| **Docker** | 컨테이너 구성 (FastAPI + PostgreSQL/PostGIS + Redis). `docker compose` |
| **tsvector + GIN** | 전체 전문검색 엔진 (아래 "검색" 참조) |
| **ETL pipeline** | 공공데이터 적재 (아래 "ETL" 참조) |
| **Anthropic SDK** | Claude API 연동 (챗봇/추천 등) — CLAUDE.md 참조 |

---

## 아키텍처 — Layered Architecture

의존성은 **위에서 아래로만** 흐른다. 상위 계층은 바로 아래 계층에만 의존하고, 하위 계층은 상위를 알지 못한다.

```
┌─────────────────────────────────────────────┐
│ 1. API Layer (Presentation)                 │  FastAPI Router, 의존성 주입, 인증
│    app/api/                                  │
├─────────────────────────────────────────────┤
│ 2. Schema Layer (DTO)                        │  Pydantic 요청/응답 모델
│    app/schemas/                              │
├─────────────────────────────────────────────┤
│ 3. Service Layer (Business Logic)           │  유스케이스, 트랜잭션 경계, 도메인 규칙
│    app/services/                             │
├─────────────────────────────────────────────┤
│ 4. Repository Layer (Data Access)           │  SQLAlchemy 쿼리, 데이터 접근 추상화
│    app/repositories/                         │
├─────────────────────────────────────────────┤
│ 5. Model Layer (Domain / ORM)               │  SQLAlchemy 모델 (database.md 매핑)
│    app/models/                               │
└─────────────────────────────────────────────┘
        │                    │
        ▼                    ▼
  Infrastructure       External
  app/core/ (DB/Redis 세션·설정·보안)
  app/etl/  (공공데이터 적재)
  app/search/ (tsvector 검색)
```

### 계층별 책임

| 계층 | 책임 | 하지 말 것 |
|---|---|---|
| **API** | 라우팅, 요청 파싱, 인증/인가, Service 호출, 응답 직렬화 | 비즈니스 로직, 직접 DB 접근 |
| **Schema** | 입출력 DTO 정의·검증 (Pydantic). ORM 모델과 분리 | ORM 모델을 그대로 응답으로 노출 |
| **Service** | 유스케이스 구현, 여러 Repository 조합, **트랜잭션 경계**, 도메인 규칙(포인트 원자 갱신 등) | HTTP·SQLAlchemy 세부에 직접 결합 |
| **Repository** | 엔티티별 CRUD·쿼리, 공간/전문검색 쿼리 캡슐화 | 비즈니스 규칙 판단 |
| **Model** | SQLAlchemy ORM 엔티티, 제약, 관계 (database.md와 1:1) | 서비스/HTTP 의존 |
| **Core/Infra** | 설정, DB/Redis 세션 팩토리, JWT/보안, 공통 예외 | 도메인 규칙 |

### 디렉토리 구조(제안)

```
app/
  main.py                # FastAPI 앱 진입점
  core/
    config.py            # 환경설정(Pydantic Settings)
    database.py          # SQLAlchemy 엔진/세션
    redis.py             # Redis 클라이언트(토큰·인증코드)
    security.py          # JWT, 비밀번호 해시
    deps.py              # 공통 의존성(DB 세션, 현재 유저)
  api/
    v1/
      auth.py            # FUNC-001
      dispositions.py    # FUNC-002
      rewards.py         # FUNC-003
      sales.py           # FUNC-004
      chat.py            # FUNC-005
      recommendations.py # FUNC-006
      coupons.py         # FUNC-007
      mypage.py          # FUNC-008
  schemas/               # Pydantic DTO
  services/              # 비즈니스 로직
  repositories/          # 데이터 접근
  models/                # SQLAlchemy 모델 (database.md 매핑)
  search/                # tsvector 전문검색
  etl/                   # 공공데이터 적재
alembic/                 # 마이그레이션
tests/
```

**트랜잭션 원칙**: 트랜잭션 경계는 Service 계층에서 관리한다. 포인트 적립/사용은 `point_transactions` 기록과 `users.point_balance`·`balance_after` 갱신을 **동일 트랜잭션**으로 처리한다(database.md 참조).

---

## 검색 — PostgreSQL `tsvector` (전체 검색 엔진)

프로젝트 전반의 텍스트 검색은 **PostgreSQL `tsvector` + GIN 인덱스**로 구현한다(별도 검색엔진 미도입).

- **검색 대상**: 상가명(`stores.store_name`, `branch_name`), 세일 상품명(`sale_products.name`), 쿠폰명(`coupons.name`), 행정처분 업체명(`admin_dispositions.business_name`).
- **방식**: 각 대상 테이블에 `tsvector` 생성 컬럼을 두고 **GIN 인덱스**를 건다. 조회는 `@@` 연산자(`to_tsquery` / `plainto_tsquery` / `websearch_to_tsquery`).
- **정규화 설정**: 한국어는 기본 형태소 파서가 없어 `'simple'` 설정을 사용한다. 부분/오타 검색이 필요하면 `pg_trgm`(트라이그램) 또는 `pg_bigm`을 보조로 병행한다(설계 메모).
- **구현 위치**: 검색 쿼리는 `app/search/` 또는 각 Repository의 전문검색 메서드로 캡슐화한다.

```sql
-- 예: 상가 전문검색 컬럼 + GIN 인덱스
ALTER TABLE stores ADD COLUMN search_tsv tsvector
  GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(store_name,'') || ' ' || coalesce(branch_name,''))
  ) STORED;
CREATE INDEX idx_stores_search ON stores USING GIN (search_tsv);

-- 세일 상품명
ALTER TABLE sale_products ADD COLUMN search_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(name,''))) STORED;
CREATE INDEX idx_sale_products_search ON sale_products USING GIN (search_tsv);

-- 조회 예시
-- SELECT * FROM stores WHERE search_tsv @@ websearch_to_tsquery('simple', :q);
```

> `search_tsv` 생성 컬럼과 GIN 인덱스는 스키마 변경이므로, 도입 시 `database.md`와 Alembic 마이그레이션에 함께 반영한다.

---

## ETL Pipeline (공공데이터 적재)

`app/etl/` 에서 **Extract → Transform → Load** 3단계로 구성한다.

1. **Extract**: 소상공인시장진흥공단 상가업소, 국토지리정보원 격자 통계, 식약처 행정처분 API/CSV 수집 → staging(raw) 적재.
2. **Transform**: 좌표계 변환(격자 UTM-K `EPSG:5179` → WGS84 `EPSG:4326`), 식약처 주소 지오코딩(주소→x/y), 지역/업종 코드 매핑, 중복 제거.
3. **Load**: 정규화 테이블(stores / admin_dispositions / grid_stats 등)로 이관하고 PostGIS `geom` 및 `tsvector` 갱신.

- 배치 재실행 안전성을 위해 upsert(멱등) 전략 사용.
- 대용량 적재 시 트랜잭션 청크 분할.

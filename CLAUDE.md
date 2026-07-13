# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

Always respond and explain in Korean (한국어) in this repository, regardless of the language the user writes in. Code, commit messages, and identifiers can stay in English as usual — this applies to explanations/communication only.

## Project status

Scaffolding exists: `pyproject.toml` (uv-managed), `Dockerfile`, `docker-compose.yml`, Alembic migrations (`alembic/versions/0001`~`0010`, full `database.md` schema incl. ETL staging tables), and a minimal `app/` tree (`core/config.py`, `core/database.py`, `core/redis.py`, `main.py` with `/health`, and a fully implemented `app/etl/` pipeline for the three public-data sources — see `develop.md` ETL 섹션). Domain layers (`api/`, `schemas/`, `services/`, `repositories/`, business `models/`) have **not** been built yet — that's the next phase, deferred until after the ETL/공공데이터 infra was in place per project sequencing.

## Goal

The project's target features and scope are documented in `goal.md` (verbatim from the original feature spec, broken down per FUNC with sub-goals). **Before starting any new feature work, check `goal.md`** to confirm what's in scope and which sub-goal it maps to — don't build functionality beyond what's listed there without confirming with the user first.

## Intended stack

- **Framework**: FastAPI
- **Runtime/server**: `uvicorn` (ASGI)
- **Package/env management**: `uv` with a `venv` (not Poetry/pip directly)
- **Containerization**: Docker
- **Databases**: PostgreSQL (primary datastore, PostGIS 권장) + Redis (refresh token, 이메일 인증코드, 캐시/세션 등 휘발성 데이터)
- **AI**: Anthropic Claude API (Python SDK, `anthropic` package)

## Commands

```bash
# Install dependencies into a uv-managed venv
uv sync

# Start Postgres(PostGIS) + Redis only (default profile)
docker compose up -d

# Run the dev server with autoreload (against the compose db/redis above)
uv run uvicorn app.main:app --reload

# Apply migrations
uv run alembic upgrade head

# Full stack in Docker (app + migrate one-shot job, profile "app")
docker compose --profile app up --build
docker compose --profile app run --rm migrate   # one-shot: alembic upgrade head

# ETL 수동 실행 (공공데이터 적재, 트리거는 수동 CLI 우선 — develop.md 참조)
uv run python -m app.etl stores --mode bulk --csv ./data/stores/2026Q1.csv
uv run python -m app.etl stores --mode api
uv run python -m app.etl grid-stats --csv ./data/grid_stats/2026.csv --metrics ./metrics.json
uv run python -m app.etl dispositions

# Run tests (once a test suite exists)
uv run pytest

# Run a single test
uv run pytest path/to/test_file.py::test_name
```

컨테이너(`app`/`migrate`)는 `POSTGRES_HOST=db`/`REDIS_HOST=redis`로 오버라이드되며, 로컬 `.env`에 `DATABASE_URL`/`REDIS_URL`을 직접 설정해뒀다면 컨테이너 실행 시엔 반드시 비워야 이 오버라이드가 적용된다(`docker-compose.yml` 참조).

## Claude API integration notes

- Use the official `anthropic` Python SDK (`pip`/`uv add anthropic`), not raw HTTP, for any Claude API calls.
- Default model: `claude-opus-4-8`, unless a specific task or cost constraint calls for `claude-sonnet-5` (cheaper, near-Opus quality on coding/agentic work) or `claude-haiku-4-5` (fastest/cheapest, for simple tasks).
- Read `ANTHROPIC_API_KEY` from the environment (via Docker/env config) — never hardcode it in source or commit it.
- For any request that may involve long input/output, default to streaming (`client.messages.stream(...)` + `.get_final_message()`) to avoid HTTP timeouts, and use adaptive thinking (`thinking={"type": "adaptive"}`) for non-trivial reasoning tasks.
- If Claude needs to call into FastAPI-side functions/tools, prefer the SDK's tool runner (`client.beta.messages.tool_runner(...)`) over hand-rolling the agentic loop.

## Database

- The DB structure is documented in `database.md`. **Whenever you write code (models, queries, migrations, API handlers), consult `database.md` first** and keep implementations consistent with it (tables, columns, relationships, indexes, constraints).
- If a schema change is needed, update `database.md` in the same change so it stays the single source of truth.
- Redis holds refresh tokens and email verification codes (not DB tables) — see the Redis section of `database.md` for key patterns and TTLs. Chatbot sessions/messages are NOT persisted to the DB.

## Architecture

- Project architecture and tech-stack conventions are in `develop.md`. **When writing code, follow its layered architecture (API → Schema → Service → Repository → Model), directory structure, and layer boundaries.**
- Tech stack: SQLAlchemy, Alembic, Docker, Redis, PostgreSQL, uv, uvicorn, venv, PostGIS + GiST, ETL pipeline — see `develop.md` for each component's role.
- **Full-text search across the project uses PostgreSQL `tsvector` + GIN indexes** (no separate search engine). See the search section of `develop.md`.
- Transaction boundaries live in the Service layer; point earn/redeem must update the ledger and cached balance atomically (see `database.md`).

## Verification loop (mandatory workflow for ALL tasks)

Every task in this repository must go through a verification loop before it's considered done:

1. Complete the work (design, code, migration, etc.).
2. Spawn a **separate verification subagent running on `sonnet`** (pass `model: "sonnet"` to the Agent tool) that checks the result strictly against the user's requirements and this repo's conventions (including `database.md`). The subagent returns a `판정: PASS` / `판정: FAIL` verdict plus specific feedback.
3. If `FAIL`, apply the feedback and re-verify. Repeat the loop until `PASS`.
4. Only report the task as done after the verifier returns `PASS`.

Keep the verifier independent from the implementation (give it the requirements + the produced artifact + a concrete checklist). Always use `sonnet` for these verification subagents.

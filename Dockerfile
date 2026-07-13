FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir uv

WORKDIR /app

# 의존성 먼저 복사해 레이어 캐시 활용
COPY pyproject.toml ./
RUN uv sync --no-dev

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000

# venv 가 이미 PATH 에 있으므로 `uv run`(런타임 재동기화로 dev 의존성까지 네트워크
# 재설치를 유발) 대신 venv 바이너리를 직접 호출한다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

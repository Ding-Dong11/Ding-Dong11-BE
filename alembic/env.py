"""Alembic 실행 환경.

접속 URL 은 환경변수에서 읽는다:
  1) DATABASE_URL 이 있으면 그대로 사용
  2) 없으면 POSTGRES_* 조합으로 조립 (psycopg v3 드라이버)

현재는 SQLAlchemy 모델 트리가 아직 없으므로 target_metadata=None 이며,
마이그레이션 파일은 op.execute(raw SQL)/op 헬퍼로 직접 작성한다.
모델(app/models)이 생기면 target_metadata 를 연결해 autogenerate 로 전환한다.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_url() -> str:
    return get_settings().sqlalchemy_database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

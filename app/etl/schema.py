"""ETL 이 직접 읽고 쓰는 테이블의 SQLAlchemy Core 정의.

app/models(ORM 도메인 모델)이 아직 없는 단계라, database.md/alembic 마이그레이션과
1:1로 맞춘 Core Table 을 이 모듈에 둔다. 추후 app/models 가 생기면 그쪽 메타데이터를
재사용하도록 교체한다 (컬럼 정의가 두 곳에서 갈라지지 않도록).
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

# ── 지역/업종 룩업 ──
sido = Table(
    "sido", metadata,
    Column("sido_code", String(10), primary_key=True),
    Column("sido_name", String(100)),
)

sigungu = Table(
    "sigungu", metadata,
    Column("sigungu_code", String(10), primary_key=True),
    Column("sido_code", String(10)),
    Column("sigungu_name", String(100)),
)

adong = Table(
    "adong", metadata,
    Column("adong_code", String(10), primary_key=True),
    Column("sigungu_code", String(10)),
    Column("adong_name", String(100)),
)

bdong = Table(
    "bdong", metadata,
    Column("bdong_code", String(10), primary_key=True),
    Column("sigungu_code", String(10)),
    Column("bdong_name", String(100)),
)

category_large = Table(
    "category_large", metadata,
    Column("large_code", String(10), primary_key=True),
    Column("large_name", String(100)),
)

category_middle = Table(
    "category_middle", metadata,
    Column("middle_code", String(10), primary_key=True),
    Column("large_code", String(10)),
    Column("middle_name", String(100)),
)

category_small = Table(
    "category_small", metadata,
    Column("small_code", String(10), primary_key=True),
    Column("middle_code", String(10)),
    Column("small_name", String(100)),
)

standard_industry = Table(
    "standard_industry", metadata,
    Column("industry_code", String(20), primary_key=True),
    Column("industry_name", String(200)),
)

disposition_types = Table(
    "disposition_types", metadata,
    Column("type_code", String(20), primary_key=True),
    Column("type_name", String(200)),
)

# ── 상가 ──
stores = Table(
    "stores", metadata,
    Column("store_id", BigInteger, primary_key=True),
    Column("store_number", String(50)),
    Column("store_name", String(200)),
    Column("branch_name", String(200)),
    Column("small_code", String(10)),
    Column("adong_code", String(10)),
    Column("bdong_code", String(10)),
    Column("industry_code", String(20)),
    Column("road_address", String(300)),
    Column("jibun_address", String(300)),
    Column("longitude", Numeric(10, 7)),
    Column("latitude", Numeric(10, 7)),
)

# ── 행정처분 ──
admin_dispositions = Table(
    "admin_dispositions", metadata,
    Column("disposition_id", BigInteger, primary_key=True),
    Column("store_id", BigInteger),
    Column("business_name", String(200)),
    Column("type_code", String(20)),
    Column("disposition_date", Date),
    Column("violation_content", Text),
    Column("legal_basis", String(300)),
    Column("authority", String(200)),
    Column("small_code", String(10)),
    Column("adong_code", String(10)),
    Column("longitude", Numeric(10, 7)),
    Column("latitude", Numeric(10, 7)),
    Column("source_seq", String(50)),
)

# ── 격자 통계 ──
grid_stats = Table(
    "grid_stats", metadata,
    Column("grid_id", String(30), primary_key=True),
    Column("center_longitude", Numeric(10, 7)),
    Column("center_latitude", Numeric(10, 7)),
    Column("min_x", Numeric(10, 7)),
    Column("min_y", Numeric(10, 7)),
    Column("max_x", Numeric(10, 7)),
    Column("max_y", Numeric(10, 7)),
)

grid_stat_metrics = Table(
    "grid_stat_metrics", metadata,
    Column("metric_code", String(30), primary_key=True),
    Column("metric_name", String(200)),
    Column("unit", String(30)),
)

grid_stat_values = Table(
    "grid_stat_values", metadata,
    Column("value_id", BigInteger, primary_key=True),
    Column("grid_id", String(30)),
    Column("metric_code", String(30)),
    Column("value", Numeric(18, 4)),
)

# ── ETL 보조 테이블 ──
etl_raw_records = Table(
    "etl_raw_records", metadata,
    Column("raw_id", BigInteger, primary_key=True),
    Column("source", String(50)),
    Column("payload", JSONB),
    Column("collected_at", DateTime(timezone=True)),
    Column("processed", Boolean),
    Column("processed_at", DateTime(timezone=True)),
)

etl_run = Table(
    "etl_run", metadata,
    Column("run_id", BigInteger, primary_key=True),
    Column("source", String(50)),
    Column("status", String(20)),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("extracted_count", Integer),
    Column("loaded_count", Integer),
    Column("failed_count", Integer),
    Column("cursor", String(200)),
    Column("error", Text),
)

raw_geocode_cache = Table(
    "raw_geocode_cache", metadata,
    Column("cache_id", BigInteger, primary_key=True),
    Column("address_hash", String(64)),
    Column("address_text", String(300)),
    Column("provider", String(20)),
    Column("longitude", Numeric(10, 7)),
    Column("latitude", Numeric(10, 7)),
    Column("created_at", DateTime(timezone=True)),
)

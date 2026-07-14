from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Identity, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DispositionType(Base):
    """database.md DISPOSITION_TYPES (섹션 12) 1:1 매핑."""

    __tablename__ = "disposition_types"

    type_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    type_name: Mapped[str] = mapped_column(String(100), nullable=False)


class AdminDisposition(Base):
    """database.md ADMIN_DISPOSITIONS (섹션 11) 1:1 매핑.

    geom / search_tsv 는 DB Generated 컬럼이라 ORM 매핑에서 제외.
    쿼리 시 text() 조건으로 직접 사용한다.
    """

    __tablename__ = "admin_dispositions"

    disposition_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    store_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stores.store_id"), nullable=True
    )
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    type_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("disposition_types.type_code"), nullable=False
    )
    disposition_date: Mapped[date] = mapped_column(Date, nullable=False)
    violation_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_basis: Mapped[str | None] = mapped_column(String(300), nullable=True)
    authority: Mapped[str | None] = mapped_column(String(200), nullable=True)
    small_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("category_small.small_code"), nullable=True
    )
    adong_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("adong.adong_code"), nullable=True
    )
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    source_seq: Mapped[str | None] = mapped_column(String(50), nullable=True)

    disposition_type: Mapped[DispositionType | None] = relationship(
        "DispositionType", lazy="select"
    )

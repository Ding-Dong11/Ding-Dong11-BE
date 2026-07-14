"""stores.image_url, sale_products.image_url 컬럼 추가

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("image_url", sa.String(500), nullable=True))
    op.add_column("sale_products", sa.Column("image_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "image_url")
    op.drop_column("sale_products", "image_url")

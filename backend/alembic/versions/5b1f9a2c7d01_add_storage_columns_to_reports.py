"""add storage columns to reports

Revision ID: 5b1f9a2c7d01
Revises: 3c8c1a0f0c12
Create Date: 2026-08-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5b1f9a2c7d01'
down_revision: Union[str, Sequence[str], None] = '3c8c1a0f0c12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("storage_key", sa.String(500), nullable=True))
    op.add_column("reports", sa.Column("storage_url", sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "storage_url")
    op.drop_column("reports", "storage_key")

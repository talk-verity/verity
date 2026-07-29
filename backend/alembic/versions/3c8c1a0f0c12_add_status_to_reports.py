"""add status to reports

Revision ID: 3c8c1a0f0c12
Revises: 97c8f536f71f
Create Date: 2026-07-28 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3c8c1a0f0c12'
down_revision: Union[str, Sequence[str], None] = '97c8f536f71f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("status", sa.String(50), nullable=False, server_default="generating"))


def downgrade() -> None:
    op.drop_column("reports", "status")

"""Partner referral codes and attribution on users."""
from alembic import op
import sqlalchemy as sa
revision = "c1f2a3b4c5d6"
down_revision = "8a2b3c4d5e6f"
branch_labels = depends_on = None


def upgrade():
    op.create_table("referral_codes",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("owner_clerk_id", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_referral_codes_owner", "referral_codes", ["owner_clerk_id"])
    op.add_column("users", sa.Column("referral_code", sa.String(64), nullable=True))
    op.create_index("ix_users_referral_code", "users", ["referral_code"])


def downgrade():
    op.drop_index("ix_users_referral_code", table_name="users")
    op.drop_column("users", "referral_code")
    op.drop_index("ix_referral_codes_owner", table_name="referral_codes")
    op.drop_table("referral_codes")

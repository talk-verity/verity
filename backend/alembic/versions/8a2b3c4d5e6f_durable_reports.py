"""Durable report jobs, request deduplication, and lookup indexes."""
from alembic import op
import sqlalchemy as sa
revision = "8a2b3c4d5e6f"
down_revision = "5b1f9a2c7d01"
branch_labels = depends_on = None

def upgrade():
    op.add_column("turns", sa.Column("request_id", sa.String(36), nullable=True))
    op.create_unique_constraint("uq_turns_request_id", "turns", ["request_id"])
    op.create_table("report_jobs",
        sa.Column("report_id", sa.String(36), sa.ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_report_jobs_status", "report_jobs", ["status"])
    for table, columns in [("turns", ["session_id", "created_at"]), ("sessions", ["user_id", "created_at"]), ("reports", ["user_id", "created_at"])]:
        op.create_index(f"ix_{table}_lookup", table, columns)
    op.execute("INSERT INTO report_jobs (report_id) SELECT id FROM reports WHERE status = 'generating'")

def downgrade():
    for table in ("turns", "sessions", "reports"):
        op.drop_index(f"ix_{table}_lookup", table)
    op.drop_table("report_jobs")
    op.drop_constraint("uq_turns_request_id", "turns", type_="unique")
    op.drop_column("turns", "request_id")

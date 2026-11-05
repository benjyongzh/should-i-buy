"""Immutable, separate research context snapshots."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "003_context_snapshots"
down_revision = "002_immutable_inputs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "context_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("series_id", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("payload", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
    )
    op.create_index("ix_context_snapshots_series_id", "context_snapshots", ["series_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER immutable_context_snapshots BEFORE UPDATE OR DELETE ON context_snapshots FOR EACH ROW EXECUTE FUNCTION trading_lab_immutable()"
        )
    elif op.get_bind().dialect.name == "sqlite":
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER immutable_context_snapshots_{action.lower()} BEFORE {action} ON context_snapshots BEGIN SELECT RAISE(ABORT, 'Immutable research input'); END"
            )


def downgrade():
    op.drop_table("context_snapshots")

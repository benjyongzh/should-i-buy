"""Immutable historical intraday, universe and event source revisions."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "004_strategy_inputs"
down_revision = "003_context_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "strategy_input_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("payload", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
    )
    op.create_index("ix_strategy_input_revisions_kind", "strategy_input_revisions", ["kind"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER immutable_strategy_input_revisions BEFORE UPDATE OR DELETE ON strategy_input_revisions FOR EACH ROW EXECUTE FUNCTION trading_lab_immutable()"
        )
    elif op.get_bind().dialect.name == "sqlite":
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER immutable_strategy_input_revisions_{action.lower()} BEFORE {action} ON strategy_input_revisions BEGIN SELECT RAISE(ABORT, 'Immutable strategy input'); END"
            )


def downgrade():
    op.drop_table("strategy_input_revisions")

"""Append-only research plans and experiment journal."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "008_research_journal"
down_revision = "007_conversation_versions"
branch_labels = None
depends_on = None


def upgrade():
    js = sa.JSON().with_variant(JSONB(), "postgresql")
    op.create_table(
        "research_studies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_id", sa.String(36), sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("research_studies.id")),
        sa.Column("request_id", sa.String(80), nullable=False, unique=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("payload", js, nullable=False),
    )
    op.create_index("ix_research_studies_strategy_id", "research_studies", ["strategy_id"])
    op.create_table(
        "research_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("study_id", sa.String(36), sa.ForeignKey("research_studies.id"), nullable=False),
        sa.Column("slot", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("payload", js, nullable=False),
        sa.UniqueConstraint("study_id", "slot"),
    )
    op.create_index("ix_research_events_study_id", "research_events", ["study_id"])
    for table in ("research_studies", "research_events"):
        if op.get_bind().dialect.name == "postgresql":
            op.execute(
                f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION trading_lab_immutable()"
            )
        else:
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'Immutable research journal'); END"
                )


def downgrade():
    op.drop_table("research_events")
    op.drop_table("research_studies")

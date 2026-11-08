"""Retained strategy conversations and streamed-turn audit snapshots."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "006_strategy_chat"
down_revision = "005_company_intakes"
branch_labels = None
depends_on = None


def upgrade():
    js = sa.JSON().with_variant(JSONB(), "postgresql")
    op.create_table(
        "strategy_chat_turns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_id", sa.String(36), sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("request_id", sa.String(80), nullable=False),
        sa.Column("source_revision", sa.Integer, nullable=False),
        sa.Column("user_text", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("context_json", js, nullable=False),
        sa.Column("reply_json", js),
        sa.Column("partial_text", sa.Text, nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("llm_proposals.id")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("strategy_id", "request_id"),
    )
    op.create_index("ix_strategy_chat_turns_strategy_id", "strategy_chat_turns", ["strategy_id"])
    op.create_index(
        "ix_chat_one_stream",
        "strategy_chat_turns",
        ["strategy_id"],
        unique=True,
        sqlite_where=sa.text("status = 'streaming'"),
        postgresql_where=sa.text("status = 'streaming'"),
    )


def downgrade():
    op.drop_table("strategy_chat_turns")

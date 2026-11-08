"""Resumable full Congress acquisition inventory, separate from source eligibility."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "009_congress_collections"
down_revision = "008_research_journal"
branch_labels = None
depends_on = None


def upgrade():
    js = sa.JSON().with_variant(JSONB(), "postgresql")

    def identity():
        return [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        ]

    op.create_table(
        "congress_collections",
        *identity(),
        sa.Column("request_id", sa.String(80), nullable=False, unique=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("request_payload", js, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("phase", sa.String(24), nullable=False),
        sa.Column("state", js, nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("worker_token", sa.String(36)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_congress_collections_status", "congress_collections", ["status"])
    op.create_table(
        "congress_collection_items",
        *identity(),
        sa.Column(
            "collection_id", sa.String(36), sa.ForeignKey("congress_collections.id"), nullable=False
        ),
        sa.Column("chamber", sa.String(8), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("report_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("request_payload", js, nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("clock_status", sa.String(24), nullable=False),
        sa.Column("official_artifact_id", sa.String(36), sa.ForeignKey("source_artifacts.id")),
        sa.Column("replay_artifact_id", sa.String(36), sa.ForeignKey("source_artifacts.id")),
        sa.Column("text_artifact_id", sa.String(36), sa.ForeignKey("source_artifacts.id")),
        sa.Column("error", sa.Text()),
        sa.UniqueConstraint("collection_id", "chamber", "year", "report_key"),
    )
    op.create_index(
        "ix_congress_collection_items_collection_id", "congress_collection_items", ["collection_id"]
    )
    op.create_index("ix_congress_collection_items_status", "congress_collection_items", ["status"])
    for table in ("congress_collections", "congress_collection_items"):
        if op.get_bind().dialect.name == "postgresql":
            op.execute(
                f"""CREATE FUNCTION {table}_request_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.request_hash IS DISTINCT FROM OLD.request_hash OR NEW.request_payload IS DISTINCT FROM OLD.request_payload THEN RAISE EXCEPTION 'Immutable Congress collection request'; END IF; RETURN NEW; END; $$"""
            )
            op.execute(
                f"CREATE TRIGGER immutable_{table}_request BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION {table}_request_immutable()"
            )
        else:
            op.execute(
                f"CREATE TRIGGER immutable_{table}_request BEFORE UPDATE OF request_hash,request_payload ON {table} WHEN NEW.request_hash != OLD.request_hash OR NEW.request_payload != OLD.request_payload BEGIN SELECT RAISE(ABORT,'Immutable Congress collection request'); END"
            )


def downgrade():
    op.drop_table("congress_collection_items")
    op.drop_table("congress_collections")
    if op.get_bind().dialect.name == "postgresql":
        for table in ("congress_collections", "congress_collection_items"):
            op.execute(f"DROP FUNCTION {table}_request_immutable()")

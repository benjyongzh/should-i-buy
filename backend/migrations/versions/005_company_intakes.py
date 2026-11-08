"""Persistent company collection jobs and immutable source evidence/packages."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "005_company_intakes"
down_revision = "004_strategy_inputs"
branch_labels = None
depends_on = None


def identity():
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade():
    js = sa.JSON().with_variant(JSONB(), "postgresql")
    op.create_table(
        "company_intakes",
        *identity(),
        sa.Column("idempotency_key", sa.String(80), nullable=False, unique=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("request_payload", js, nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("progress", sa.Integer, nullable=False),
        sa.Column("cancel_requested", sa.Boolean, nullable=False),
        sa.Column("worker_token", sa.String(36)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text),
    )
    for col in ["request_hash", "status"]:
        op.create_index("ix_company_intakes_" + col, "company_intakes", [col])
    op.create_table(
        "source_artifacts",
        *identity(),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("metadata_json", js, nullable=False),
        sa.Column("body", sa.LargeBinary, nullable=False),
    )
    op.create_index("ix_source_artifacts_content_hash", "source_artifacts", ["content_hash"])
    op.create_table(
        "intake_artifacts",
        sa.Column(
            "intake_id", sa.String(36), sa.ForeignKey("company_intakes.id"), primary_key=True
        ),
        sa.Column(
            "artifact_id", sa.String(36), sa.ForeignKey("source_artifacts.id"), primary_key=True
        ),
    )
    op.create_table(
        "intake_reports",
        *identity(),
        sa.Column(
            "intake_id",
            sa.String(36),
            sa.ForeignKey("company_intakes.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("payload", js, nullable=False),
    )
    op.create_table(
        "company_packages",
        *identity(),
        sa.Column("intake_id", sa.String(36), sa.ForeignKey("company_intakes.id"), nullable=False),
        sa.Column("report_id", sa.String(36), sa.ForeignKey("intake_reports.id"), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("payload", js, nullable=False),
    )
    op.create_index("ix_company_packages_intake_id", "company_packages", ["intake_id"])
    dialect = op.get_bind().dialect.name
    for table in ["source_artifacts", "intake_artifacts", "intake_reports", "company_packages"]:
        if dialect == "postgresql":
            op.execute(
                f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION trading_lab_immutable()"
            )
        elif dialect == "sqlite":
            for action in ["update", "delete"]:
                op.execute(
                    f"CREATE TRIGGER immutable_{table}_{action} BEFORE {action.upper()} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable source evidence'); END"
                )
    if dialect == "postgresql":
        op.execute("""CREATE FUNCTION trading_lab_intake_request_immutable() RETURNS trigger AS $$
        BEGIN IF NEW.request_payload IS DISTINCT FROM OLD.request_payload OR NEW.request_hash IS DISTINCT FROM OLD.request_hash OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key THEN
        RAISE EXCEPTION 'immutable intake request'; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql""")
        op.execute(
            "CREATE TRIGGER immutable_intake_request BEFORE UPDATE ON company_intakes FOR EACH ROW EXECUTE FUNCTION trading_lab_intake_request_immutable()"
        )
    elif dialect == "sqlite":
        op.execute("""CREATE TRIGGER immutable_intake_request BEFORE UPDATE OF request_payload, request_hash, idempotency_key ON company_intakes
        WHEN NEW.request_payload != OLD.request_payload OR NEW.request_hash != OLD.request_hash OR NEW.idempotency_key != OLD.idempotency_key
        BEGIN SELECT RAISE(ABORT, 'immutable intake request'); END""")


def downgrade():
    for table in [
        "company_packages",
        "intake_reports",
        "intake_artifacts",
        "source_artifacts",
        "company_intakes",
    ]:
        op.drop_table(table)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION trading_lab_intake_request_immutable()")

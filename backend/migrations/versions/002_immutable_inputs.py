"""Enforce append-only research inputs at the database boundary."""

from alembic import op

revision = "002_immutable_inputs"
down_revision = "e7ce119c0ee5"
branch_labels = None
depends_on = None

TABLES = ("strategy_versions", "market_datasets", "candles", "fx_rates", "corporate_actions")


def upgrade():
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            "CREATE FUNCTION trading_lab_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Immutable research input cannot be updated or deleted'; END; $$"
        )
        for table in TABLES:
            op.execute(
                f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION trading_lab_immutable()"
            )
    elif dialect == "sqlite":
        for table in TABLES:
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'Immutable research input'); END"
                )


def downgrade():
    dialect = op.get_bind().dialect.name
    for table in TABLES:
        if dialect == "postgresql":
            op.execute(f"DROP TRIGGER immutable_{table} ON {table}")
        elif dialect == "sqlite":
            for action in ("update", "delete"):
                op.execute(f"DROP TRIGGER immutable_{table}_{action}")
    if dialect == "postgresql":
        op.execute("DROP FUNCTION trading_lab_immutable()")

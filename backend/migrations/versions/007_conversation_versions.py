"""One conversation per strategy; ordered immutable turns and version transcripts."""

import hashlib
import json
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "007_conversation_versions"
down_revision = "006_strategy_chat"
branch_labels = None
depends_on = None


def stamp(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def upgrade():
    js = sa.JSON().with_variant(JSONB(), "postgresql")
    op.create_table(
        "strategy_conversations",
        sa.Column("strategy_id", sa.String(36), sa.ForeignKey("strategies.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("strategy_chat_turns", sa.Column("sequence", sa.Integer, nullable=True))
    bind = op.get_bind()
    metadata = sa.MetaData()
    strategies = sa.Table("strategies", metadata, autoload_with=bind)
    turns = sa.Table("strategy_chat_turns", metadata, autoload_with=bind)
    conversations = sa.Table("strategy_conversations", metadata, autoload_with=bind)
    for strategy in bind.execute(sa.select(strategies.c.id, strategies.c.created_at)).mappings():
        bind.execute(
            conversations.insert().values(
                strategy_id=strategy["id"], created_at=strategy["created_at"]
            )
        )
        for sequence, turn in enumerate(
            bind.execute(
                sa.select(turns.c.id)
                .where(turns.c.strategy_id == strategy["id"])
                .order_by(turns.c.created_at, turns.c.id)
            ),
            1,
        ):
            bind.execute(turns.update().where(turns.c.id == turn.id).values(sequence=sequence))
    with op.batch_alter_table("strategy_chat_turns") as batch:
        batch.alter_column("sequence", existing_type=sa.Integer, nullable=False)
    op.create_index(
        "ix_chat_sequence", "strategy_chat_turns", ["strategy_id", "sequence"], unique=True
    )
    op.create_table(
        "version_conversations",
        sa.Column(
            "version_id", sa.String(36), sa.ForeignKey("strategy_versions.id"), primary_key=True
        ),
        sa.Column(
            "strategy_id",
            sa.String(36),
            sa.ForeignKey("strategy_conversations.strategy_id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("payload", js, nullable=False),
    )
    op.create_index(
        "ix_version_conversations_strategy_id", "version_conversations", ["strategy_id"]
    )
    snapshots = sa.Table("version_conversations", metadata, autoload_with=bind)
    versions = sa.Table("strategy_versions", metadata, autoload_with=bind)
    for version in bind.execute(sa.select(versions)).mappings():
        boundary = stamp(version["created_at"])
        records = []
        for row in bind.execute(
            sa.select(turns)
            .where(turns.c.strategy_id == version["strategy_id"])
            .order_by(turns.c.sequence)
        ).mappings():
            if stamp(row["created_at"]) > boundary:
                continue
            item = {
                key: stamp(value).isoformat() if isinstance(value, datetime) else value
                for key, value in row.items()
            }
            if row["completed_at"] is None or stamp(row["completed_at"]) > boundary:
                item.update(
                    status="in_progress_at_publication",
                    completed_at=None,
                    reply_json=None,
                    partial_text="",
                    error=None,
                    proposal_id=None,
                )
            records.append(item)
        payload = {
            "conversation_id": version["strategy_id"],
            "version_id": version["id"],
            "origin": "legacy_timestamp_boundary" if records else "legacy_no_retained_conversation",
            "published_at": boundary.isoformat(),
            "through_sequence": max((r["sequence"] for r in records), default=0),
            "turns": records,
        }
        payload.update(
            strategy_config_hash=version["config_hash"],
            draft_revision_at_publication=None,
            accepted_chat_turn_id=(version["llm_metadata"] or {}).get("chat_turn_id"),
            manual_edits_after_proposal=bool(
                (version["llm_metadata"] or {}).get("manually_edited_after_acceptance")
            ),
        )
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        bind.execute(
            snapshots.insert().values(
                version_id=version["id"],
                strategy_id=version["strategy_id"],
                created_at=datetime.now(UTC),
                content_hash=digest,
                payload=payload,
            )
        )
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER immutable_strategy_conversations BEFORE UPDATE OR DELETE ON strategy_conversations FOR EACH ROW EXECUTE FUNCTION trading_lab_immutable()"
        )
        op.execute(
            "CREATE TRIGGER immutable_version_conversations BEFORE UPDATE OR DELETE ON version_conversations FOR EACH ROW EXECUTE FUNCTION trading_lab_immutable()"
        )
        op.execute("""CREATE FUNCTION trading_lab_chat_final_immutable() RETURNS trigger AS $$
        BEGIN IF OLD.status <> 'streaming' THEN RAISE EXCEPTION 'Immutable finalized conversation turn'; END IF;
        IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql""")
        op.execute(
            "CREATE TRIGGER immutable_final_chat_turn BEFORE UPDATE OR DELETE ON strategy_chat_turns FOR EACH ROW EXECUTE FUNCTION trading_lab_chat_final_immutable()"
        )
    elif bind.dialect.name == "sqlite":
        for action in ["UPDATE", "DELETE"]:
            op.execute(
                f"CREATE TRIGGER immutable_strategy_conversations_{action.lower()} BEFORE {action} ON strategy_conversations BEGIN SELECT RAISE(ABORT, 'Immutable strategy conversation identity'); END"
            )
            op.execute(
                f"CREATE TRIGGER immutable_version_conversations_{action.lower()} BEFORE {action} ON version_conversations BEGIN SELECT RAISE(ABORT, 'Immutable version conversation'); END"
            )
            op.execute(
                f"CREATE TRIGGER immutable_final_chat_turn_{action.lower()} BEFORE {action} ON strategy_chat_turns WHEN OLD.status != 'streaming' BEGIN SELECT RAISE(ABORT, 'Immutable finalized conversation turn'); END"
            )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER immutable_final_chat_turn ON strategy_chat_turns")
        op.execute("DROP FUNCTION trading_lab_chat_final_immutable()")
    else:
        for action in ["update", "delete"]:
            op.execute(f"DROP TRIGGER IF EXISTS immutable_final_chat_turn_{action}")
    op.drop_table("version_conversations")
    op.drop_index("ix_chat_sequence", table_name="strategy_chat_turns")
    with op.batch_alter_table("strategy_chat_turns") as batch:
        batch.drop_column("sequence")
    op.drop_table("strategy_conversations")

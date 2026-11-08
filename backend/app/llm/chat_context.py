"""Bounded server-built evidence. No remote browsing or model-selected source URLs."""

from datetime import UTC, datetime

from app.api.routes import get
from app.llm.chat_contracts import ChatSelection
from app.models.entities import (
    BacktestRun,
    Dataset,
    Profile,
    ResearchStudy,
    StrategyInputRevision,
    StrategyVersion,
)
from app.schemas.domain import canonical_hash
from app.services.datasets import load_dataset
from app.services.strategy_inputs import checked_input


def build_context(db, strategy, selection: ChatSelection):
    now = datetime.now(UTC)
    cutoff = selection.as_of or now
    if cutoff > now:
        raise ValueError("research evidence cutoff cannot be in the future")
    evidence = []
    profile = get(db, Profile, selection.profile_id) if selection.profile_id else None
    symbols = set(profile.config["symbols"]) if profile else None
    if selection.dataset_id:
        row = get(db, Dataset, selection.dataset_id)
        data = load_dataset(db, row)
        visible = [
            b
            for b in data.bars
            if b.available_at <= cutoff and (symbols is None or b.symbol in symbols)
        ]
        summaries = []
        for symbol in sorted({b.symbol for b in visible})[:5]:
            bars = sorted((b for b in visible if b.symbol == symbol), key=lambda b: b.session_date)
            summaries.append(
                {
                    "symbol": symbol,
                    "first_session": str(bars[0].session_date),
                    "last_session": str(bars[-1].session_date),
                    "visible_bars": len(bars),
                    "first_close_usd": str(bars[0].close),
                    "last_close_usd": str(bars[-1].close),
                    "last_available_at": bars[-1].available_at.isoformat(),
                    "note": "Raw nominal closes, not split-adjusted total return; do not infer return across splits.",
                }
            )
        evidence.append(
            {
                "id": row.id,
                "kind": "accounting_dataset",
                "name": row.name,
                "content_hash": row.content_hash,
                "synthetic": row.synthetic,
                "reviewed": data.corporate_actions_reviewed,
                "source_url": None,
                "provider": row.provider,
                "summary": summaries,
                "availability_policy": data.availability_policy,
            }
        )
    for identifier in dict.fromkeys(selection.strategy_input_ids):
        row = get(db, StrategyInputRevision, identifier)
        data = checked_input(row)
        events = [
            e
            for e in data.events
            if e.published_at <= cutoff
            and e.available_at <= cutoff
            and e.access == "public"
            and (symbols is None or not e.symbols or symbols.intersection(e.symbols))
        ]
        evidence.append(
            {
                "id": row.id,
                "kind": data.kind,
                "name": data.name,
                "content_hash": row.content_hash,
                "reviewed": data.reviewed,
                "synthetic": data.synthetic,
                "source_url": data.source_url,
                "availability_policy": data.availability_policy,
                "summary": {
                    "stream_id": data.stream_id,
                    "visible_public_events": len(events),
                    "recent_events": [
                        {
                            "title": e.title,
                            "published_at": e.published_at.isoformat(),
                            "available_at": e.available_at.isoformat(),
                            "source_url": e.source_url,
                        }
                        for e in sorted(events, key=lambda e: e.available_at)[-8:]
                    ],
                    "note": "Only public event summaries retrieved; no article text, analyst score, intraday bars or security states retrieved into this conversation.",
                },
            }
        )
    for identifier in dict.fromkeys(selection.run_ids):
        row = get(db, BacktestRun, identifier)
        if row.status != "completed" or row.result is None:
            raise ValueError("only completed runs can supply research evidence")
        version = get(db, StrategyVersion, row.strategy_version_id)
        last_mark = row.result.get("equity", [])[-1:]
        if row.profile_snapshot["end_date"] > cutoff.date().isoformat() or (
            last_mark
            and datetime.fromisoformat(last_mark[0]["timestamp"].replace("Z", "+00:00")) > cutoff
        ):
            raise ValueError("run results extend beyond the selected research cutoff")
        evidence.append(
            {
                "id": row.id,
                "kind": "backtest_result",
                "name": "Completed research run",
                "content_hash": canonical_hash(row.result),
                "synthetic": row.provenance.get("synthetic", False),
                "reviewed": False,
                "source_url": None,
                "availability_policy": "Retrospective in-sample simulation, not an observed market forecast.",
                "summary": {
                    "metrics": row.result["metrics"],
                    "profile_snapshot": row.profile_snapshot,
                    "strategy_version_id": row.strategy_version_id,
                    "strategy_config": version.config,
                    "strategy_config_hash": version.config_hash,
                    "strategy_version_number": version.number,
                    "provenance": row.provenance,
                },
            }
        )
    if selection.study_ids:
        from app.analytics.periods import period_report
        from app.api.journal import events, run_snapshot, stamp

        for identifier in dict.fromkeys(selection.study_ids):
            row = get(db, ResearchStudy, identifier)
            if row.strategy_id != strategy.id:
                raise ValueError("Research plan belongs to another strategy conversation")
            if stamp(row.created_at) > cutoff:
                raise ValueError("Research plan did not exist at the selected cutoff")
            records = [e for e in events(db, row) if stamp(e.created_at) <= cutoff]
            attempts = []
            for record in records:
                if record.kind != "run":
                    continue
                run = get(db, BacktestRun, record.payload["run_id"])
                if run.completed_at and stamp(run.completed_at) <= cutoff:
                    snapshot = run_snapshot(run)
                    if run.status == "completed" and run.result is not None:
                        snapshot["yearly_periods"] = period_report(run.result, run.profile_snapshot)
                    attempts.append(snapshot)
                else:
                    attempts.append({"id": run.id, "status": "outcome_not_available_at_cutoff"})
            baseline = get(db, BacktestRun, row.payload["baseline"]["id"])
            if (
                baseline.result is None
                or canonical_hash(baseline.result) != row.payload["baseline"]["result_hash"]
            ):
                raise ValueError("Journal baseline result no longer matches its frozen hash")
            summary = {
                "baseline_yearly_periods": period_report(
                    baseline.result, baseline.profile_snapshot
                ),
                "plan": row.payload,
                "events": [
                    {
                        "kind": e.kind,
                        "created_at": stamp(e.created_at).isoformat(),
                        "payload": e.payload,
                    }
                    for e in records
                ],
                "attempts": attempts,
            }
            evidence.append(
                {
                    "id": row.id,
                    "kind": "research_journal",
                    "name": row.payload["question"],
                    "content_hash": canonical_hash(summary),
                    "synthetic": row.payload["provenance"].get("synthetic", False),
                    "reviewed": False,
                    "source_url": None,
                    "availability_policy": "Human-authored research plan and recorded in-sample outcomes; not historical market observations or a forecast. Later journal events/outcomes are withheld.",
                    "summary": summary,
                }
            )
    context = {
        "strategy_id": strategy.id,
        "draft_revision": strategy.draft_revision,
        "draft": strategy.draft,
        "selection": selection.model_dump(mode="json"),
        "evidence_cutoff": cutoff.isoformat(),
        "profile": profile.config if profile else None,
        "evidence": evidence,
        "retrieval": "Only explicitly selected local revisions/results; no web search or new vendor fetch.",
        "estimates_are_research_only": True,
    }
    context["context_hash"] = canonical_hash(context)
    return context

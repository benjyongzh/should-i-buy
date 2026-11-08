from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.market_data.calendar import decision_timestamp, session_times, sessions
from app.market_data.providers import AlpacaProvider
from app.market_data.validation import validate_coverage, validate_dataset
from app.market_data.view import fx_at
from app.models.entities import Dataset, StrategyInputRevision
from app.onboarding.contracts import SUPPORTED, IntakeRequest
from app.onboarding.proposals import proposals
from app.onboarding.sources import SourceClient, alpaca_actions, resolve_identity, sec_filings
from app.schemas.domain import ProfileConfig
from app.services.datasets import import_dataset, load_dataset
from app.services.strategy_inputs import checked_input, retain_input

NY = ZoneInfo("America/New_York")


def collect(db: Session, intake_id: str, request: IntakeRequest, checkpoint):
    client = SourceClient(db, intake_id, checkpoint)
    first = request.start - timedelta(days=request.warmup_days)
    days = sessions(first, request.end)
    trade_days = sessions(request.start, request.end)
    if not days or not trade_days:
        raise ValueError("requested interval has no exchange sessions")
    coverage_start = datetime.combine(
        trade_days[0] - timedelta(days=request.event_lookback_days), time(), NY
    )
    coverage_end = datetime.combine(request.end, time.max, NY)
    report = {
        "intake_id": intake_id,
        "request": request.model_dump(mode="json"),
        "identity": None,
        "capabilities": {
            c: {
                "state": "blocked",
                "reason": "Collector for this capability is not implemented; use its existing reviewed import path.",
            }
            for c in request.capabilities
        },
        "checks": [],
        "findings": [],
        "candidate_dataset_id": None,
        "candidate_source_id": None,
        "reused_action_symbols": [],
        "upstream_dataset_ids": [],
        "actions": [],
        "action_proposals": [],
        "coverage_start": coverage_start.isoformat(),
        "coverage_end": coverage_end.isoformat(),
    }

    def finding(cap, message):
        report["findings"].append({"capability": cap, "message": message})
        if cap in report["capabilities"]:
            report["capabilities"][cap] = {"state": "blocked", "reason": message}

    try:
        report["identity"] = resolve_identity(client, request.symbol)
    except ValueError as error:
        for cap in set(request.capabilities) & SUPPORTED:
            finding(cap, str(error))
        return finish(report, client)

    rows = list(
        db.scalars(
            select(Dataset)
            .where(Dataset.synthetic.is_(False))
            .order_by(Dataset.created_at.desc())
            .limit(200)
        )
    )
    loaded = {}

    def load(row):
        if row.id not in loaded:
            loaded[row.id] = load_dataset(db, row)
        return loaded[row.id]

    def covers(row, symbols):
        cov = row.metadata_json.get("coverage", {})
        return all(
            s in cov
            and cov[s]["start"] <= str(days[0])
            and cov[s]["end"] >= str(days[-1])
            and not cov[s]["missing_sessions"]
            for s in symbols
        )

    def reviewed(row):
        return row.metadata_json.get("corporate_actions_reviewed") and row.metadata_json.get(
            "dividends_complete"
        )

    required = sorted({request.symbol, request.benchmark})
    if "daily_accounting" in request.capabilities:
        profile = ProfileConfig(
            symbols=[request.symbol],
            benchmark=request.benchmark,
            start_date=request.start,
            end_date=request.end,
            account_currency=request.account_currency,
            max_fx_age_days=request.max_fx_age_days,
        )
        reused = None
        if not request.refresh:
            for row in [r for r in rows if covers(r, required) and reviewed(r)][:5]:
                try:
                    validate_coverage(load(row), profile)
                    reused = row
                    break
                except ValueError:
                    pass
        if reused:
            report["candidate_dataset_id"] = reused.id
            report["upstream_dataset_ids"].append(reused.id)
            report["reused_action_symbols"] = required
            report["capabilities"]["daily_accounting"] = {
                "state": "reviewed",
                "reason": "Existing immutable reviewed dataset covers requested sessions, benchmark and FX policy.",
                "dataset_id": reused.id,
            }
        else:
            try:
                data = AlpacaProvider(client.capture).fetch(
                    required, first, request.end, feed="sip"
                )
                report["candidate_dataset_id"] = import_dataset(db, data).id
                cov = validate_dataset(data)
                missing = {
                    s: sorted(set(days) - {b.session_date for b in data.bars if b.symbol == s})
                    for s in required
                }
                if any(missing.values()):
                    raise ValueError(
                        "Missing requested raw price sessions; no data substitution permitted"
                    )
                report["checks"].append(
                    {"check": "raw_daily_session_coverage", "status": "pass", "coverage": cov}
                )
                for symbol in required:
                    upstream = next(
                        (
                            r
                            for r in rows
                            if reviewed(r) and covers(r, [symbol]) and not request.refresh
                        ),
                        None,
                    )
                    if upstream:
                        report["upstream_dataset_ids"].append(upstream.id)
                        report["reused_action_symbols"].append(symbol)
                fx_source = None
                if request.account_currency == "SGD":
                    for row in [
                        r for r in rows if reviewed(r) and r.metadata_json.get("fx_observations", 0)
                    ][:5]:
                        fx = load(row).fx
                        try:
                            for day in trade_days:
                                for clock in (
                                    *session_times(day),
                                    decision_timestamp(day, data.decision_time),
                                ):
                                    fx_at(fx, clock, request.max_fx_age_days)
                            fx_source = row.id
                            break
                        except ValueError:
                            pass
                    if fx_source is None:
                        raise ValueError(
                            "No reviewed historical USD/SGD revision covers every required clock; import/review FX first"
                        )
                report["fx_dataset_id"] = fx_source
                report["actions"] = (
                    alpaca_actions(
                        client,
                        [s for s in required if s not in report["reused_action_symbols"]],
                        first,
                        request.end,
                    )
                    if set(required) - set(report["reused_action_symbols"])
                    else []
                )
                report["capabilities"]["daily_accounting"] = {
                    "state": "needs_review",
                    "reason": "Raw prices and broker action candidates collected. Original issuer evidence and complete split/dividend coverage require explicit review.",
                }
            except ValueError as error:
                finding("daily_accounting", str(error))

    # Reuse complete reviewed filing streams when their symbol/clock scope matches.
    reused_source = None
    if not request.refresh and "sec_filings" in request.capabilities:
        for row in db.scalars(
            select(StrategyInputRevision)
            .where(StrategyInputRevision.kind == "events")
            .order_by(StrategyInputRevision.created_at.desc())
            .limit(300)
        ):
            source = checked_input(row)
            if (
                source.reviewed
                and source.complete
                and not source.synthetic
                and source.stream_id == "SEC_FILINGS"
                and request.symbol in source.symbols
                and source.coverage_start <= coverage_start
                and source.coverage_end >= coverage_end
            ):
                reused_source = row
                break
    if reused_source:
        report["candidate_source_id"] = reused_source.id
        report["capabilities"]["sec_filings"] = {
            "state": "reviewed",
            "reason": "Existing reviewed SEC stream covers this symbol and the requested information clocks.",
            "source_id": reused_source.id,
        }
    elif "sec_filings" in request.capabilities or report["actions"]:
        try:
            sec_start = (
                min(first - timedelta(days=90), coverage_start.date() - timedelta(days=14))
                if report["actions"]
                else coverage_start.date() - timedelta(days=14)
            )
            source, documents = sec_filings(
                client,
                report["identity"],
                sec_start,
                request.end,
                coverage_start,
                coverage_end,
                request.max_sec_documents,
            )
            report["documents"] = documents
            if "sec_filings" in request.capabilities:
                report["candidate_source_id"] = retain_input(db, source).id
                report["capabilities"]["sec_filings"] = {
                    "state": "needs_review",
                    "reason": "Complete inventory and retained primary documents checked. Next-session-close clock proxy and additive amendments require explicit review.",
                }
        except ValueError as error:
            finding("sec_filings", str(error))
            if report["actions"]:
                report["findings"].append(
                    {
                        "capability": "daily_accounting",
                        "message": "Issuer evidence collection incomplete; supply original evidence for action candidates.",
                    }
                )
    report["action_proposals"] = proposals(report["actions"], client.artifacts)
    return finish(report, client)


def finish(report, client):
    report["artifacts"] = [
        {
            "id": a.id,
            "kind": a.kind,
            "source_url": a.source_url,
            "content_hash": a.content_hash,
            "bytes": a.metadata_json["bytes"],
            "metadata": a.metadata_json,
        }
        for a in client.artifacts
    ]
    report["source_bytes"] = client.bytes
    report["policies"] = [
        "Current SEC ticker mapping does not prove historical share-class continuity; reviewer must attest it.",
        "Current raw SIP prices use assumed 20:15 New York availability; decisions at 20:30 New York, not original vendor vintages.",
        "SEC publication/availability modeled at next full exchange session CLOSE after acceptance; not exact first-public time.",
        "Broker corporate actions are candidates only. Original issuer evidence, nominal share basis and missing fields require review.",
        "SGD uses an explicitly reused reviewed reference-FX policy and the requested maximum age; not executable FX.",
        "No historical sectors, comprehensive news, unsupported terminal actions, intraday fills or broker execution are inferred.",
    ]
    return report

"""Explicit evidence review creates new immutable revisions; collection never approves."""

from sqlalchemy import select

from app.market_data.calendar import sessions
from app.market_data.strategy_inputs import StrategyInput
from app.market_data.validation import validate_coverage, validate_dataset
from app.models.entities import CompanyPackage, Dataset, IntakeReport, StrategyInputRevision
from app.onboarding.contracts import IntakeRequest, IntakeReview
from app.onboarding.evidence import checked_artifact, date_in_text, plain_text, source_available_at
from app.onboarding.proposals import money_in_text, ratio_in_text
from app.schemas.domain import DatasetInput, ProfileConfig, canonical_hash
from app.services.datasets import import_dataset, load_dataset
from app.services.strategy_inputs import checked_input, resolve_inputs, retain_input


def checked_report(row):
    if row is None or canonical_hash(row.payload) != row.content_hash:
        raise ValueError("intake report content hash mismatch or report unavailable")
    return row.payload


def action_key(action):
    return action.symbol, action.session_date.isoformat(), action.kind


def evidence_action(db, intake_id, proof):
    action = proof.action
    artifact = checked_artifact(db, intake_id, proof.artifact_id)
    if (
        artifact.kind not in {"sec_submission", "issuer_evidence"}
        or artifact.metadata_json.get("symbol") != action.symbol
    ):
        raise ValueError("action requires original issuer evidence for the same symbol")
    quote = " ".join(proof.quote.split())
    if quote not in plain_text(artifact.body):
        raise ValueError("action quote is absent from retained evidence")
    available = source_available_at(artifact)
    if available is None or action.available_at < available:
        raise ValueError("action availability precedes retained evidence availability")
    if action.kind == "dividend":
        if not money_in_text(action.value, quote) or not date_in_text(action.payment_date, quote):
            raise ValueError(
                "issuer quote must support the nominal dividend amount and payment date"
            )
    elif not ratio_in_text(action.value, quote) or not date_in_text(action.session_date, quote):
        raise ValueError("issuer quote must support the split ratio and effective date")
    return action


def approve(db, intake, body: IntakeReview):
    report_row = db.scalar(select(IntakeReport).where(IntakeReport.intake_id == intake.id))
    report = checked_report(report_row)
    if intake.status != "awaiting_review" or body.expected_report_hash != report_row.content_hash:
        raise ValueError("review requires the completed, unchanged collection report")
    if canonical_hash(intake.request_payload) != intake.request_hash:
        raise ValueError("intake request content hash mismatch")
    request = IntakeRequest.model_validate(intake.request_payload)
    if (
        report.get("intake_id") != intake.id
        or canonical_hash(report["request"]) != intake.request_hash
    ):
        raise ValueError("report/request identity mismatch")
    for item in report["artifacts"]:
        artifact = checked_artifact(db, intake.id, item["id"])
        if (
            artifact.content_hash != item["content_hash"]
            or artifact.metadata_json != item["metadata"]
        ):
            raise ValueError("report evidence identity mismatch")
    for cap in body.approve_capabilities:
        if cap not in report["capabilities"] or report["capabilities"][cap]["state"] not in {
            "reviewed",
            "needs_review",
        }:
            raise ValueError(
                f"{cap} is blocked or was not requested; collect a new report after resolving it"
            )
    if report.get("identity") is None:
        raise ValueError("verified company identity is required")
    prepared_data = prepared_source = dataset_row = source_row = None
    # Preflight every requested approval before retaining any eligible output.
    if "daily_accounting" in body.approve_capabilities:
        dataset_row = db.get(Dataset, report["candidate_dataset_id"])
        data = load_dataset(db, dataset_row)
        if data.synthetic:
            raise ValueError("company onboarding requires real data")
        profile = ProfileConfig(
            symbols=[request.symbol],
            benchmark=request.benchmark,
            start_date=request.start,
            end_date=request.end,
            account_currency=request.account_currency,
            max_fx_age_days=request.max_fx_age_days,
        )
        if report["capabilities"]["daily_accounting"]["state"] == "reviewed":
            if body.actions:
                raise ValueError(
                    "reused immutable accounting cannot be amended; request a fresh collection"
                )
            validate_coverage(data, profile)
        else:
            if not body.attest_action_coverage:
                raise ValueError(
                    "attest complete split/dividend coverage, including no-event intervals"
                )
            keys = [action_key(p.action) for p in body.actions]
            if len(keys) != len(set(keys)):
                raise ValueError("duplicate action review")
            candidates = {
                (
                    r["record"]["symbol"],
                    r["record"]["ex_date"],
                    "dividend" if r["kind"] == "cash_dividends" else "split",
                )
                for r in report["actions"]
            }
            if not candidates.issubset(set(keys)):
                raise ValueError(
                    "every broker action candidate requires issuer evidence; none may be omitted"
                )
            bar_keys = {(b.symbol, b.session_date) for b in data.bars}
            for proof in body.actions:
                if (
                    proof.action.symbol in report["reused_action_symbols"]
                    or (proof.action.symbol, proof.action.session_date) not in bar_keys
                ):
                    raise ValueError("reviewed action is outside the new symbol/session scope")
            actions = [evidence_action(db, intake.id, p) for p in body.actions]
            for identifier in set(report["upstream_dataset_ids"]):
                upstream = load_dataset(db, db.get(Dataset, identifier))
                if (
                    upstream.synthetic
                    or not upstream.corporate_actions_reviewed
                    or not upstream.dividends_complete
                ):
                    raise ValueError("upstream action coverage must be real and reviewed")
                actions.extend(
                    a
                    for a in upstream.actions
                    if a.symbol in report["reused_action_symbols"]
                    and (a.symbol, a.session_date) in bar_keys
                )
            fx = (
                load_dataset(db, db.get(Dataset, report["fx_dataset_id"])).fx
                if report.get("fx_dataset_id")
                else []
            )
            payload = data.model_dump(mode="json")
            payload.update(
                name=f"{request.symbol} reviewed intake {intake.id}",
                actions=[a.model_dump(mode="json") for a in actions],
                fx=[r.model_dump(mode="json") for r in fx],
                corporate_actions_reviewed=True,
                dividends_complete=True,
                availability_policy=data.availability_policy[:290]
                + " Review/FX/action lineage: "
                + report_row.content_hash,
            )
            prepared_data = DatasetInput.model_validate(payload)
            validate_dataset(prepared_data)
            validate_coverage(prepared_data, profile)
        from datetime import timedelta

        needed = sessions(request.start - timedelta(days=request.warmup_days), request.end)
        keys = {(b.symbol, b.session_date) for b in data.bars}
        if any((s, d) not in keys for s in {request.symbol, request.benchmark} for d in needed):
            raise ValueError("warm-up/session coverage is incomplete")
    elif body.actions:
        raise ValueError("action evidence is only accepted with daily accounting review")
    if "sec_filings" in body.approve_capabilities:
        source_row = db.get(StrategyInputRevision, report["candidate_source_id"])
        source = checked_input(source_row)
        if (
            source.synthetic
            or source.stream_id != "SEC_FILINGS"
            or request.symbol not in source.symbols
        ):
            raise ValueError("SEC source identity mismatch")
        if source.reviewed:
            resolve_inputs(db, [source_row.id])
        else:
            payload = source.model_dump(mode="json")
            payload.update(
                reviewed=True,
                complete=True,
                parent_id=source_row.id,
                parent_hash=source_row.content_hash,
                review_note=body.note,
            )
            prepared_source = StrategyInput.model_validate(payload)
    if prepared_data:
        dataset_row = import_dataset(db, prepared_data, commit=False)
    if prepared_source:
        source_row = retain_input(db, prepared_source, commit=False)
    payload = {
        "intake_id": intake.id,
        "request_hash": intake.request_hash,
        "report_hash": report_row.content_hash,
        "ready_capabilities": sorted(body.approve_capabilities),
        "dataset": {"id": dataset_row.id, "content_hash": dataset_row.content_hash}
        if dataset_row
        else None,
        "strategy_inputs": [{"id": source_row.id, "content_hash": source_row.content_hash}]
        if source_row
        else [],
        "review": body.model_dump(mode="json"),
        "policies": report["policies"],
        "evidence": [
            {
                "id": p.artifact_id,
                "content_hash": checked_artifact(db, intake.id, p.artifact_id).content_hash,
            }
            for p in body.actions
        ],
        "scope": request.model_dump(mode="json"),
        "strategy_readiness_required": True,
    }
    digest = canonical_hash(payload)
    package = db.scalar(select(CompanyPackage).where(CompanyPackage.content_hash == digest))
    if package is None:
        package = CompanyPackage(
            intake_id=intake.id, report_id=report_row.id, content_hash=digest, payload=payload
        )
        db.add(package)
        db.commit()
    return package

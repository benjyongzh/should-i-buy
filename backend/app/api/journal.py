"""Human research decisions around existing immutable versions and backtest runs."""

from datetime import UTC
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.contracts import Schedule
from app.api.routes import dump, get, schedule_runs
from app.backtesting.engine import ENGINE_VERSION
from app.db.session import get_db
from app.models.entities import (
    BacktestRun,
    Profile,
    ResearchEvent,
    ResearchStudy,
    Strategy,
    StrategyChatTurn,
    StrategyVersion,
    VersionConversation,
)
from app.schemas.domain import StrictModel, canonical_hash

router = APIRouter(prefix="/api/research/studies", tags=["research journal"])
CONTROL_KEYS = (
    "engine_version",
    "execution_model",
    "indicator_version",
    "dataset_hash",
    "profile_hash",
    "external_input_hash",
    "strategy_input_hash",
)


class Plan(StrictModel):
    request_id: str = Field(min_length=1, max_length=80)
    baseline_run_id: str
    question: str = Field(min_length=10, max_length=2000)
    hypothesis: str = Field(min_length=10, max_length=4000)
    planned_change: str = Field(min_length=10, max_length=4000)
    evaluation_criteria: str = Field(min_length=10, max_length=4000)
    mode: Literal["prospective", "retrospective"] = "prospective"
    parent_id: str | None = None


class Candidate(StrictModel):
    strategy_version_id: str


class Attempt(StrictModel):
    request_id: str = Field(min_length=1, max_length=80)
    acknowledge_synthetic: bool = False


class Attach(StrictModel):
    run_id: str


class Note(StrictModel):
    request_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=4000)


class Conclusion(StrictModel):
    assessment: Literal["improved", "worse", "mixed", "inconclusive"]
    summary: str = Field(min_length=10, max_length=4000)
    next_hypothesis: str = Field(default="", max_length=4000)


def stamp(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def controls(run):
    return {key: run.provenance.get(key) for key in CONTROL_KEYS}


def run_snapshot(run):
    return {
        "id": run.id,
        "strategy_version_id": run.strategy_version_id,
        "status": run.status,
        "error": run.error,
        "completed_at": stamp(run.completed_at).isoformat() if run.completed_at else None,
        "result_hash": canonical_hash(run.result)
        if run.status == "completed" and run.result is not None
        else None,
        "metrics": {
            key: value
            for key, value in run.result["metrics"].items()
            if value is None or isinstance(value, (str, int, float, bool))
        }
        if run.status == "completed" and run.result is not None
        else None,
    }


def differences(before, after):
    """Exact decimal differences of stored scalar metrics, not new financial metrics."""
    result = {}
    for key in before.keys() & after.keys():
        try:
            a, b = Decimal(str(before[key])), Decimal(str(after[key]))
            if a.is_finite() and b.is_finite():
                result[key] = str(b - a)
        except (InvalidOperation, ValueError, TypeError):
            continue
    return result


def events(db, study):
    return list(
        db.scalars(
            select(ResearchEvent)
            .where(ResearchEvent.study_id == study.id)
            .order_by(ResearchEvent.created_at, ResearchEvent.id)
        )
    )


def existing(db, study, slot):
    return db.scalar(
        select(ResearchEvent).where(ResearchEvent.study_id == study.id, ResearchEvent.slot == slot)
    )


def locked(db, identifier):
    row = db.scalar(select(ResearchStudy).where(ResearchStudy.id == identifier).with_for_update())
    if row is None:
        raise HTTPException(404, "Research plan not found")
    return row


def require_open(db, study):
    if existing(db, study, "conclusion"):
        raise HTTPException(
            409, "Plan concluded; create a follow-on plan to continue experimentation"
        )


def append(db, study, slot, kind, payload):
    prior = existing(db, study, slot)
    if prior:
        if prior.kind != kind or prior.payload != payload:
            raise HTTPException(
                409, "Request identifier already used for different journal content"
            )
        return prior
    count = db.scalar(
        select(func.count()).select_from(ResearchEvent).where(ResearchEvent.study_id == study.id)
    )
    if count >= 500:
        raise HTTPException(409, "Journal limit reached; create a follow-on plan")
    row = ResearchEvent(
        study_id=study.id,
        slot=slot,
        kind=kind,
        payload=payload,
        content_hash=canonical_hash(payload),
    )
    db.add(row)
    db.flush()
    return row


def detail(db, study):
    records = events(db, study)
    attempts = []
    for record in records:
        if record.kind == "run":
            run = get(db, BacktestRun, record.payload["run_id"])
            snapshot = run_snapshot(run)
            snapshot["metric_deltas"] = (
                differences(study.payload["baseline"]["metrics"], snapshot["metrics"])
                if snapshot["metrics"]
                else {}
            )
            attempts.append(snapshot)
    return {
        **dump(study),
        "events": [dump(row) for row in records],
        "attempts": attempts,
        "state": "concluded" if any(row.kind == "conclusion" for row in records) else "open",
    }


@router.get("")
def studies(
    strategy_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = select(ResearchStudy)
    if strategy_id:
        query = query.where(ResearchStudy.strategy_id == strategy_id)
    return [
        dump(row)
        for row in db.scalars(query.order_by(ResearchStudy.created_at.desc()).limit(limit))
    ]


@router.get("/{identifier}")
def study(identifier: str, db: Session = Depends(get_db)):
    return detail(db, get(db, ResearchStudy, identifier))


@router.post("", status_code=201)
def register(body: Plan, db: Session = Depends(get_db)):
    request_hash = canonical_hash(body.model_dump(mode="json"))
    prior = db.scalar(select(ResearchStudy).where(ResearchStudy.request_id == body.request_id))
    if prior:
        if prior.request_hash != request_hash:
            raise HTTPException(409, "Request identifier already used for another plan")
        return detail(db, prior)
    run = get(db, BacktestRun, body.baseline_run_id)
    if run.status != "completed" or run.result is None:
        raise ValueError("Baseline must be a completed run with retained results")
    version = get(db, StrategyVersion, run.strategy_version_id)
    db.scalar(select(Strategy).where(Strategy.id == version.strategy_id).with_for_update())
    if db.scalar(
        select(StrategyChatTurn.id).where(
            StrategyChatTurn.strategy_id == version.strategy_id,
            StrategyChatTurn.status == "streaming",
        )
    ):
        raise HTTPException(
            409, "Wait for the strategy conversation to finish before registering a plan"
        )
    if body.parent_id:
        parent = get(db, ResearchStudy, body.parent_id)
        if parent.strategy_id != version.strategy_id:
            raise ValueError("Follow-on plans must belong to the same strategy")
    profile = Profile(name="Research journal frozen profile", config=run.profile_snapshot)
    db.add(profile)
    db.flush()
    checkpoint = (
        db.scalar(
            select(func.max(StrategyChatTurn.sequence)).where(
                StrategyChatTurn.strategy_id == version.strategy_id
            )
        )
        or 0
    )
    payload = {
        **body.model_dump(mode="json", exclude={"request_id", "parent_id"}),
        "baseline": run_snapshot(run),
        "baseline_config": version.config,
        "profile_snapshot": run.profile_snapshot,
        "profile_id": profile.id,
        "dataset_id": run.dataset_id,
        "provenance": run.provenance,
        "controls": controls(run),
        "conversation_through_sequence": checkpoint,
        "warning": "Repeated evaluation of the same historical period is in-sample research; improvements do not establish future performance.",
    }
    row = ResearchStudy(
        strategy_id=version.strategy_id,
        parent_id=body.parent_id,
        request_id=body.request_id,
        request_hash=request_hash,
        payload=payload,
        content_hash=canonical_hash(payload),
    )
    db.add(row)
    db.commit()
    return detail(db, row)


@router.post("/{identifier}/candidate")
def candidate(identifier: str, body: Candidate, db: Session = Depends(get_db)):
    row = locked(db, identifier)
    version = get(db, StrategyVersion, body.strategy_version_id)
    if (
        version.strategy_id != row.strategy_id
        or version.id == row.payload["baseline"]["strategy_version_id"]
    ):
        raise ValueError("Candidate must be another published version of this strategy")
    if row.payload["mode"] == "prospective" and stamp(version.created_at) < stamp(row.created_at):
        raise ValueError(
            "Prospective candidates must be published after plan registration; label existing-version analysis retrospective"
        )
    payload = {
        "strategy_version_id": version.id,
        "number": version.number,
        "config": version.config,
        "config_hash": version.config_hash,
    }
    transcript = db.get(VersionConversation, version.id)
    payload["conversation_hash"] = transcript.content_hash if transcript else None
    prior = existing(db, row, "candidate")
    if prior and prior.payload == payload:
        return detail(db, row)
    require_open(db, row)
    append(db, row, "candidate", "candidate", payload)
    db.commit()
    return detail(db, row)


def check_run(row, candidate_event, run):
    if run.strategy_version_id != candidate_event.payload["strategy_version_id"]:
        raise ValueError("Run does not use the bound candidate version")
    if (
        controls(run) != row.payload["controls"]
        or run.profile_snapshot != row.payload["profile_snapshot"]
        or run.dataset_id != row.payload["dataset_id"]
    ):
        raise ValueError("Run does not match frozen profile, dataset, sources and engine controls")
    if row.payload["mode"] == "prospective" and stamp(run.created_at) < stamp(row.created_at):
        raise ValueError("Prospective attempts must be created after registration")


@router.post("/{identifier}/schedule", status_code=202)
def schedule(identifier: str, body: Attempt, db: Session = Depends(get_db)):
    row = locked(db, identifier)
    slot = "schedule:" + body.request_id
    prior = existing(db, row, slot)
    if prior:
        if prior.payload["request"] != body.model_dump(mode="json"):
            raise HTTPException(
                409, "Request identifier already used with other scheduling parameters"
            )
        return detail(db, row)
    require_open(db, row)
    bound = existing(db, row, "candidate")
    if not bound:
        raise ValueError("Bind a reviewed published candidate before scheduling")
    if row.payload["controls"]["engine_version"] != ENGINE_VERSION:
        raise ValueError("Engine has changed; establish a baseline under the current engine")
    provenance = row.payload["provenance"]
    profile = get(db, Profile, row.payload["profile_id"])
    if profile.config != row.payload["profile_snapshot"]:
        raise ValueError(
            "Journal profile was edited; restore its frozen configuration before scheduling"
        )
    request = Schedule(
        strategy_version_ids=[bound.payload["strategy_version_id"]],
        profile_id=profile.id,
        dataset_id=row.payload["dataset_id"],
        experiment_name="Journal: " + row.payload["question"][:140],
        acknowledge_synthetic=body.acknowledge_synthetic,
        context_snapshot_ids=[x["snapshot_id"] for x in provenance.get("external_inputs", [])],
        strategy_input_ids=[x["snapshot_id"] for x in provenance.get("strategy_inputs", [])],
    )
    runs = schedule_runs(request, db, commit=False)
    run = get(db, BacktestRun, runs[0]["id"])
    check_run(row, bound, run)
    append(db, row, slot, "run", {"run_id": run.id, "request": body.model_dump(mode="json")})
    db.commit()
    return detail(db, row)


@router.post("/{identifier}/runs")
def attach(identifier: str, body: Attach, db: Session = Depends(get_db)):
    row = locked(db, identifier)
    run = get(db, BacktestRun, body.run_id)
    if any(e.kind == "run" and e.payload["run_id"] == run.id for e in events(db, row)):
        return detail(db, row)
    require_open(db, row)
    bound = existing(db, row, "candidate")
    if not bound:
        raise ValueError("Bind a candidate first")
    check_run(row, bound, run)
    append(db, row, "run:" + run.id, "run", {"run_id": run.id, "attached": True})
    db.commit()
    return detail(db, row)


@router.post("/{identifier}/notes")
def note(identifier: str, body: Note, db: Session = Depends(get_db)):
    row = locked(db, identifier)
    append(db, row, "note:" + body.request_id, "note", body.model_dump(mode="json"))
    db.commit()
    return detail(db, row)


@router.post("/{identifier}/conclusion")
def conclude(identifier: str, body: Conclusion, db: Session = Depends(get_db)):
    row = locked(db, identifier)
    prior = existing(db, row, "conclusion")
    if prior:
        if (
            prior.payload["assessment"] == body.assessment
            and prior.payload["summary"] == body.summary
            and prior.payload["next_hypothesis"] == body.next_hypothesis
        ):
            return detail(db, row)
        raise HTTPException(
            409, "Conclusion is immutable; append a note or create a follow-on plan"
        )
    attempts = detail(db, row)["attempts"]
    if not attempts:
        raise ValueError("Record at least one candidate attempt before concluding")
    if any(r["status"] in ("queued", "running") for r in attempts):
        raise ValueError("Wait for all recorded attempts to reach a terminal state")
    if body.assessment != "inconclusive" and not any(r["status"] == "completed" for r in attempts):
        raise ValueError(
            "An outcome requires completed candidate results; failures may be concluded inconclusive"
        )
    append(
        db, row, "conclusion", "conclusion", {**body.model_dump(mode="json"), "attempts": attempts}
    )
    db.commit()
    return detail(db, row)

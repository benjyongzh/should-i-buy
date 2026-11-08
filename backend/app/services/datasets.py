import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.market_data.validation import validate_dataset
from app.models.entities import Candle, CorporateAction, Dataset, FXRate
from app.schemas.domain import DatasetInput, canonical_hash

logger = logging.getLogger(__name__)


def content(data: DatasetInput) -> dict:
    payload = data.model_dump(mode="json", exclude={"name"})
    if data.decision_time == "close_plus_30m":
        payload.pop("decision_time")
    if not data.corporate_actions_reviewed:
        payload.pop("corporate_actions_reviewed")
    payload["bars"].sort(key=lambda b: (b["symbol"], b["session_date"]))
    payload["fx"].sort(key=lambda r: (r["observed_at"], r["available_at"]))
    payload["actions"].sort(key=lambda a: (a["symbol"], a["session_date"], a["kind"]))
    return payload


def import_dataset(db: Session, data: DatasetInput, *, commit: bool = True) -> Dataset:
    if len(data.bars) > settings().max_dataset_rows:
        raise ValueError("dataset exceeds configured row limit")
    coverage = validate_dataset(data)
    digest = canonical_hash(content(data))
    existing = db.scalar(select(Dataset).where(Dataset.content_hash == digest))
    if existing:
        return existing
    dataset = Dataset(
        name=data.name,
        provider=data.provider,
        synthetic=data.synthetic,
        content_hash=digest,
        metadata_json={
            "coverage": coverage,
            "adjustment_policy": data.adjustment_policy,
            "dividends_complete": data.dividends_complete,
            "corporate_actions_reviewed": data.corporate_actions_reviewed,
            "availability_policy": data.availability_policy,
            "decision_time": data.decision_time,
            "fx_observations": len(data.fx),
            "actions": len(data.actions),
        },
    )
    db.add(dataset)
    db.flush()
    db.add_all(
        Candle(
            dataset_id=dataset.id,
            symbol=b.symbol,
            session_date=b.session_date,
            payload=b.model_dump(mode="json"),
        )
        for b in data.bars
    )
    db.add_all(
        FXRate(
            dataset_id=dataset.id,
            observed_at=r.observed_at,
            available_at=r.available_at,
            payload=r.model_dump(mode="json"),
        )
        for r in data.fx
    )
    db.add_all(
        CorporateAction(dataset_id=dataset.id, payload=a.model_dump(mode="json"))
        for a in data.actions
    )
    if commit:
        db.commit()
    else:
        db.flush()
    logger.info(
        "dataset_imported" if commit else "dataset_staged",
        extra={"dataset_id": dataset.id, "rows": len(data.bars)},
    )
    return dataset


def load_dataset(db: Session, dataset: Dataset) -> DatasetInput:
    data = DatasetInput(
        name=dataset.name,
        provider=dataset.provider,
        synthetic=dataset.synthetic,
        adjustment_policy=dataset.metadata_json["adjustment_policy"],
        dividends_complete=dataset.metadata_json["dividends_complete"],
        corporate_actions_reviewed=dataset.metadata_json.get("corporate_actions_reviewed", False),
        availability_policy=dataset.metadata_json["availability_policy"],
        decision_time=dataset.metadata_json.get("decision_time", "close_plus_30m"),
        bars=list(db.scalars(select(Candle.payload).where(Candle.dataset_id == dataset.id))),
        fx=list(db.scalars(select(FXRate.payload).where(FXRate.dataset_id == dataset.id))),
        actions=list(
            db.scalars(
                select(CorporateAction.payload).where(CorporateAction.dataset_id == dataset.id)
            )
        ),
    )
    if canonical_hash(content(data)) != dataset.content_hash:
        raise ValueError("dataset content hash mismatch; refusing non-reproducible input")
    return data

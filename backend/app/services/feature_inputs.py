"""Resolve immutable, explicitly reviewed snapshots at scheduling/worker boundaries."""

from sqlalchemy.orm import Session

from app.market_data.context import ContextData
from app.market_data.features import FeatureBook, FeaturePoint, FeatureSeries
from app.models.entities import ContextSnapshot
from app.schemas.domain import canonical_hash


def context_content_hash(payload: dict) -> str:
    return canonical_hash({k: v for k, v in payload.items() if k != "retrieved_at"})


def checked_context(row: ContextSnapshot) -> ContextData:
    data = ContextData.model_validate(row.payload)
    if row.series_id != data.series_id or context_content_hash(row.payload) != row.content_hash:
        raise ValueError("External snapshot content hash mismatch")
    return data


def as_feature(data: ContextData, digest: str) -> FeatureSeries:
    if any(point.available_at is None for point in data.observations):
        raise ValueError(
            "Unknown publication availability cannot drive trades; import a timestamped source revision"
        )
    return FeatureSeries(
        series_id=data.series_id,
        content_hash=digest,
        synthetic=data.synthetic,
        points=[
            FeaturePoint(
                observation_date=p.observation_date, available_at=p.available_at, value=p.value
            )
            for p in data.observations
        ],
    )


def resolve_features(db: Session, identifiers: list[str]) -> tuple[list[dict], list[FeatureSeries]]:
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate external snapshot selection")
    bindings, series = [], []
    for identifier in identifiers:
        row = db.get(ContextSnapshot, identifier)
        if row is None:
            raise ValueError("External snapshot not found")
        data = checked_context(row)
        if data.research_only:
            raise ValueError(
                "External snapshot is viewing-only; explicitly review a new strategy-eligible revision first"
            )
        parent = db.get(ContextSnapshot, data.source_snapshot_id)
        if parent is None or parent.content_hash != data.source_snapshot_hash:
            raise ValueError("External source-review lineage mismatch")
        checked_context(parent)
        series.append(as_feature(data, row.content_hash))
        bindings.append(
            {
                "snapshot_id": row.id,
                "series_id": row.series_id,
                "content_hash": row.content_hash,
                "synthetic": data.synthetic,
            }
        )
    FeatureBook(series)  # Enforce unique series and global size limits before queueing.
    return sorted(bindings, key=lambda b: b["series_id"]), series


def frozen_features(db: Session, provenance: dict) -> list[FeatureSeries]:
    bindings = provenance.get("external_inputs", [])
    if context_content_hash({"bindings": bindings}) != provenance.get(
        "external_input_hash", context_content_hash({"bindings": []})
    ):
        raise ValueError("Frozen external-input manifest hash mismatch")
    current, series = resolve_features(db, [binding["snapshot_id"] for binding in bindings])
    if current != bindings:
        raise ValueError("Frozen external snapshot identity/hash mismatch")
    return series

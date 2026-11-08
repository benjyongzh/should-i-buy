"""Explicit canonical identities and causal source-version reconciliation, not a PDF parser."""

from collections import defaultdict
from datetime import datetime
from decimal import localcontext

from app.congress.contracts import LedgerRequest, Observation
from app.congress.evidence import checked, index_rows, public_bound
from app.market_data.strategy_inputs import CongressDetails, HistoricalEvent, StrategyInput
from app.schemas.domain import canonical_hash

POLICY_VERSION = "house-canonical-observed-versions-v1"
MAX_EVIDENCE_BYTES = 64_000_000
CATEGORIES = [
    "congress_equity_purchase",
    "congress_equity_sale",
    "congress_equity_exchange",
    "congress_call_option_purchase",
    "congress_call_option_sale",
    "congress_call_option_exchange",
    "congress_put_option_purchase",
    "congress_put_option_sale",
    "congress_put_option_exchange",
    "congress_option_exercise",
    "congress_charitable_transfer",
    "congress_other_purchase",
    "congress_other_sale",
    "congress_other_exchange",
]


def category(row: Observation):
    if row.action in ("unknown",) or row.instrument == "unknown":
        return None
    if row.action in ("option_exercise", "charitable_transfer"):
        return "congress_" + row.action
    return f"congress_{row.instrument}_{row.action}"


def economic_facts(row: Observation):
    facts = row.model_dump(
        mode="json",
        include={
            "reporter",
            "owner",
            "symbol",
            "issuer_cik",
            "instrument",
            "action",
            "transaction_date",
            "amount_min",
            "amount_max",
            "shares",
            "option_contracts",
            "strike_usd",
        },
    )

    # Disclosed numeric formatting is not another economic fact or trade signal.
    with localcontext() as context:
        context.prec = 34
        for field in ("amount_min", "amount_max", "shares", "option_contracts", "strike_usd"):
            value = getattr(row, field)
            if value is not None:
                facts[field] = format(value.normalize(), "f")
    return facts


def reconcile(rows: list[Observation], proofs: dict):
    by_id = {row.observation_id: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("duplicate disclosure observation identity")
    groups = defaultdict(list)
    for row in rows:
        groups[row.canonical_transaction_id].append(row)
    events = []
    audit = []
    blockers = []
    for canonical, group in sorted(groups.items()):
        anchors = {(r.reporter, r.owner, r.symbol, r.issuer_cik) for r in group}
        if len(anchors) != 1:
            raise ValueError(
                "canonical identity cannot merge different reporter/owner/issuer facts"
            )
        roots = [r for r in group if not r.amends_observation_id]
        if len(roots) != 1:
            raise ValueError(
                "each canonical transaction requires exactly one retained original; identical rows are not automatically merged"
            )
        children = defaultdict(list)
        for row in group:
            if row.amends_observation_id:
                parent = by_id.get(row.amends_observation_id)
                if (
                    parent is None
                    or parent.canonical_transaction_id != canonical
                    or parent.filing_date > row.filing_date
                ):
                    raise ValueError(
                        "amendment requires an earlier-filed retained predecessor in the same canonical transaction"
                    )
                if (
                    proofs[parent.observation_id]["document_id"]
                    == proofs[row.observation_id]["document_id"]
                ):
                    raise ValueError("an amendment must reference a different filing document")
                children[parent.observation_id].append(row)
        if any(len(items) > 1 for items in children.values()):
            raise ValueError(
                "branching amendment lineage requires explicit resolution before normalization"
            )
        ranks = {}
        current = roots[0]
        while current is not None:
            if current.observation_id in ranks:
                raise ValueError("cyclic amendment lineage")
            ranks[current.observation_id] = len(ranks)
            current = children.get(current.observation_id, [None])[0]
        if len(ranks) != len(group):
            raise ValueError("disconnected or cyclic amendment lineage")
        for row in group:
            if proofs[row.observation_id]["clock"] is None:
                blockers.append(f"{row.observation_id}: missing verified public observation")
            if category(row) is None or row.amount_min is None:
                blockers.append(
                    f"{row.observation_id}: unresolved instrument/action/amount; no trade signal fabricated"
                )
        clocks = sorted(
            {
                proofs[r.observation_id]["clock"]
                for r in group
                if proofs[r.observation_id]["clock"] is not None
            }
        )
        latest_rank = -1
        last_facts = None
        previous_event = None
        for clock in clocks:
            visible = [
                r
                for r in group
                if proofs[r.observation_id]["clock"] is not None
                and proofs[r.observation_id]["clock"] <= clock
            ]
            winner = max(visible, key=lambda r: ranks[r.observation_id])
            newly_seen = [
                r.observation_id for r in group if proofs[r.observation_id]["clock"] == clock
            ]
            facts = canonical_hash(economic_facts(winner))
            disposition = (
                "older_filing_observed_late"
                if ranks[winner.observation_id] == latest_rank
                else "metadata_only_amendment"
                if facts == last_facts
                else "economic_observation"
            )
            event_id = None
            if facts != last_facts and ranks[winner.observation_id] >= latest_rank:
                name = category(winner)
                if name is not None and winner.amount_min is not None:
                    proof = proofs[winner.observation_id]
                    event_id = (
                        "house-"
                        + canonical_hash({"canonical": canonical})[:20]
                        + "-"
                        + canonical_hash(
                            {
                                "observation": winner.observation_id,
                                "clock": clock.isoformat(),
                                "facts": facts,
                            }
                        )[:20]
                    )
                    event = HistoricalEvent(
                        event_id=event_id,
                        published_at=clock,
                        available_at=clock,
                        category=name,
                        tags=[
                            "house_disclosure",
                            winner.owner,
                            "instrument:" + winner.instrument,
                            "action:" + winner.action,
                        ],
                        symbols=[winner.symbol],
                        title=f"{winner.reporter} {winner.owner}: {winner.symbol} {winner.action} ({winner.instrument}); transaction {winner.transaction_date}",
                        source_url=proof["replay_url"],
                        original_content_hash=proof["content_hash"],
                        derivation="Explicitly reconciled canonical transaction under "
                        + POLICY_VERSION
                        + ". Exact-PDF public-observation bound, not first-public release; notification/filing dates are not clocks. Later capture of older disclosure cannot duplicate or revert the transaction.",
                        supersedes_event_id=previous_event,
                        details=CongressDetails(
                            type="congress",
                            chamber="house",
                            filing_id=proof["document_id"],
                            reporter=winner.reporter,
                            owner=winner.owner,
                            transaction=winner.action,
                            transaction_date=winner.transaction_date,
                            public_at=clock,
                            amount_min=winner.amount_min,
                            amount_max=winner.amount_max,
                            instrument=winner.instrument,
                            canonical_transaction_id=canonical,
                            observation_id=winner.observation_id,
                            reported_transaction_code=winner.reported_transaction_code,
                        ),
                    )
                    events.append(event)
                    previous_event = event_id
            audit.append(
                {
                    "canonical_transaction_id": canonical,
                    "observed_at": clock.isoformat(),
                    "newly_observed_ids": newly_seen,
                    "selected_observation_id": winner.observation_id,
                    "selected_filing_rank": ranks[winner.observation_id],
                    "disposition": disposition,
                    "event_id": event_id,
                }
            )
            latest_rank = ranks[winner.observation_id]
            last_facts = facts
    return sorted(events, key=lambda e: (e.available_at, e.event_id)), audit, blockers


def prepare(db, request: LedgerRequest):
    index = checked(db, request.index_artifact_id, "house_fd_index")
    if index.metadata_json.get("synthetic") and not request.synthetic:
        raise ValueError("synthetic source evidence cannot be relabeled real")
    if index.metadata_json["year"] != request.filing_start.year:
        raise ValueError("filing domain does not match the retained index year")
    reporter = f"{request.first_name} {request.last_name}"
    supporting = [
        checked(db, identifier, "house_fd_index")
        for identifier in request.supporting_index_artifact_ids
    ]
    indices = [index, *supporting]
    if len({row.id for row in indices}) != len(indices):
        raise ValueError("duplicate supporting index artifact")
    if not request.synthetic and any(row.metadata_json.get("synthetic") for row in indices):
        raise ValueError("synthetic source evidence cannot be relabeled real")
    inventory = []
    filer_rows = {}
    for snapshot in indices:
        for row in index_rows(snapshot):
            if (
                row.get("FilingType") != "P"
                or (row.get("First", "").strip() + " " + row.get("Last", "").strip()).casefold()
                != reporter.casefold()
            ):
                continue
            day = datetime.strptime(row["FilingDate"], "%m/%d/%Y").date()
            identity = (day, snapshot.metadata_json["year"])
            if row["DocID"] in filer_rows and filer_rows[row["DocID"]] != identity:
                raise ValueError("conflicting report identity across retained indexes")
            filer_rows[row["DocID"]] = identity
            if snapshot.id == index.id and request.filing_start <= day <= request.filing_end:
                inventory.append(row)
    if not inventory:
        raise ValueError(
            "no matching PTR filings in the retained index; empty scope requires separate review"
        )
    expected = {
        r["DocID"]: datetime.strptime(r["FilingDate"], "%m/%d/%Y").date() for r in inventory
    }
    report_proofs = {}
    blockers = []
    proof_hashes = {row.content_hash for row in indices}
    proof_cache = {}
    evidence_seen = {row.id for row in indices}
    evidence_bytes = sum(len(row.body) for row in indices)

    def proof(official_id, replay_id):
        nonlocal evidence_bytes
        key = (official_id, replay_id)
        if key in proof_cache:
            return proof_cache[key]
        official = checked(db, official_id, "house_ptr")
        if official.metadata_json.get("synthetic") and not request.synthetic:
            raise ValueError("synthetic source evidence cannot be relabeled real")
        replay = checked(db, replay_id, "house_ptr_replay") if replay_id else None
        for artifact in (official, replay):
            if artifact is not None and artifact.id not in evidence_seen:
                evidence_bytes += len(artifact.body)
                evidence_seen.add(artifact.id)
        if evidence_bytes > MAX_EVIDENCE_BYTES:
            raise ValueError(
                "Congress ledger evidence budget exceeds64MB; use a smaller filing cohort"
            )
        clock, findings = public_bound(official, replay)
        if official.metadata_json["http_status"] != 200:
            raise ValueError("official report unavailable; cannot review its rows")
        proof_hashes.add(official.content_hash)
        if replay:
            proof_hashes.add(replay.content_hash)
        proof_cache[key] = {
            "document_id": official.metadata_json["document_id"],
            "year": official.metadata_json["year"],
            "clock": clock,
            "replay_url": replay.source_url if replay else None,
            "content_hash": official.content_hash,
            "findings": findings,
        }
        return proof_cache[key]

    for review in request.report_reviews:
        item = proof(review.official_artifact_id, review.replay_artifact_id)
        if item["document_id"] in report_proofs:
            raise ValueError("duplicate reviewed report")
        report_proofs[item["document_id"]] = item
        blockers.extend(f"{item['document_id']}: {x}" for x in item["findings"])
    if set(report_proofs) != set(expected):
        blockers.append(
            "Reviewed report inventory does not exactly match the selected official filing domain"
        )
    proofs = {}
    for row in request.observations:
        if row.reporter != reporter:
            raise ValueError("observation reporter does not match filing-domain reporter")
        item = proof(row.official_artifact_id, row.replay_artifact_id)
        if filer_rows.get(item["document_id"]) != (row.filing_date, item["year"]):
            raise ValueError(
                "supporting original/amendment must match this reporter and filing date in the retained official index"
            )
        if item["document_id"] in expected and row.filing_date != expected[item["document_id"]]:
            raise ValueError("observation filing date does not match official index")
        if item["clock"] and item["clock"].date() < row.filing_date:
            raise ValueError("archival public observation cannot precede the filing date")
        proofs[row.observation_id] = item
    for review in request.report_reviews:
        doc = checked(db, review.official_artifact_id, "house_ptr").metadata_json["document_id"]
        matched = [
            row for row in request.observations if proofs[row.observation_id]["document_id"] == doc
        ]
        if (review.disposition == "selected_rows") != bool(matched):
            raise ValueError("report disposition conflicts with selected rows")
    grouped = defaultdict(list)
    for row in request.observations:
        grouped[row.canonical_transaction_id].append(row)
    if any(
        not any(proofs[r.observation_id]["document_id"] in expected for r in group)
        for group in grouped.values()
    ):
        raise ValueError("supporting original is not linked to a selected-domain transaction")
    events, audit, issues = reconcile(request.observations, proofs)
    blockers.extend(issues)
    if any(not request.coverage_start <= e.published_at <= request.coverage_end for e in events):
        raise ValueError(
            "canonical event lies outside the explicitly declared observation coverage"
        )
    policy = f"{POLICY_VERSION}. Bounded House filing cohort only: {reporter}, filed {request.filing_start} through {request.filing_end}, symbols {','.join(request.symbols)}; supporting originals included for the same canonical transactions. Current official index plus explicitly reviewed PDFs. Verified archived exact-byte/Memento observation bounds, NOT first-public timestamps or all-Congress coverage. No inference of real-world trade absence before a bound. No metadata-only re-signal or late-original reversion. Manual row transcription and identity/lineage review; not an automatic PDF parser."
    source = StrategyInput(
        kind="events",
        name=request.name,
        source="house-canonical-reviewed-observation-cohort",
        source_url="https://disclosures-clerk.house.gov/FinancialDisclosure",
        availability_policy=policy,
        synthetic=request.synthetic,
        coverage_start=request.coverage_start,
        coverage_end=request.coverage_end,
        symbols=request.symbols,
        stream_id=request.stream_id,
        source_hashes=sorted(proof_hashes),
        category_catalog=sorted(set(CATEGORIES) | {t for e in events for t in e.tags}),
        events=events,
    )
    return {
        "policy_version": POLICY_VERSION,
        "request": request.model_dump(mode="json"),
        "inventory": inventory,
        "canonical_transactions": [
            {"canonical_transaction_id": key, "observations": [r.observation_id for r in group]}
            for key, group in sorted(grouped.items())
        ],
        "clock_audit": audit,
        "blockers": sorted(set(blockers)),
        "source": source.model_dump(mode="json"),
        "review_warning": "Approval is an explicit review of this named filing cohort and conservative observation policy, not a complete Congress trade feed or original first-public archive.",
    }

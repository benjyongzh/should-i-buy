import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes import dump, get
from app.core.config import settings
from app.db.session import get_db
from app.llm.client import PROMPT_VERSION, CompatibleAuthor
from app.models.entities import LLMProposal, Strategy
from app.schemas.domain import StrategyConfig, StrictModel

router = APIRouter(prefix="/api/llm")


class AuthorRequest(StrictModel):
    strategy_id: str
    prompt: str = Field(min_length=1, max_length=5000)


@router.get("/proposals/{identifier}")
def retained_proposal(identifier: str, db: Session = Depends(get_db)):
    return dump(get(db, LLMProposal, identifier))


@router.post("/plan-strategy")
def plan(body: AuthorRequest, db: Session = Depends(get_db)):
    from app.api.strategy_inputs import describe_capabilities

    strategy = get(db, Strategy, body.strategy_id)
    proposed = CompatibleAuthor().plan(body.prompt, strategy.draft)
    blocked = proposed.config is None or bool(proposed.unsupported_requests)
    proposal = LLMProposal(
        strategy_id=strategy.id,
        source_revision=strategy.draft_revision,
        config=proposed.config.model_dump(mode="json") if proposed.config else {},
        metadata_json={
            "model": settings().llm_model,
            "prompt_version": PROMPT_VERSION,
            "prompt": body.prompt,
            "prompt_hash": hashlib.sha256(body.prompt.encode()).hexdigest(),
            "blocked": blocked,
            "interpretation": proposed.interpretation,
            "assumptions": proposed.assumptions,
            "data_requirements": proposed.data_requirements,
            "unsupported_requests": proposed.unsupported_requests,
            "capabilities": describe_capabilities(proposed.config) if proposed.config else None,
        },
    )
    db.add(proposal)
    db.commit()
    return dump(proposal)


@router.post("/generate-strategy")
@router.post("/modify-strategy")
def propose(body: AuthorRequest, db: Session = Depends(get_db)):
    strategy = get(db, Strategy, body.strategy_id)
    config = CompatibleAuthor().propose(body.prompt, strategy.draft)
    proposal = LLMProposal(
        strategy_id=strategy.id,
        source_revision=strategy.draft_revision,
        config=config.model_dump(mode="json"),
        metadata_json={
            "model": settings().llm_model,
            "prompt_version": PROMPT_VERSION,
            "prompt": body.prompt,
            "prompt_hash": hashlib.sha256(body.prompt.encode()).hexdigest(),
        },
    )
    db.add(proposal)
    db.commit()
    return dump(proposal)


@router.post("/proposals/{identifier}/accept")
def accept(identifier: str, db: Session = Depends(get_db)):
    proposal = get(db, LLMProposal, identifier)
    strategy = db.scalar(
        select(Strategy).where(Strategy.id == proposal.strategy_id).with_for_update()
    )
    if proposal.accepted or proposal.source_revision != strategy.draft_revision:
        raise HTTPException(409, "Proposal was accepted or draft changed; request a fresh proposal")
    if proposal.metadata_json.get("blocked") or proposal.metadata_json.get("unsupported_requests"):
        raise ValueError(
            "proposal contains unsupported requests; revise it instead of accepting a silent approximation"
        )
    strategy.draft = StrategyConfig.model_validate(proposal.config).model_dump(mode="json")
    strategy.llm_metadata = proposal.metadata_json
    strategy.draft_revision += 1
    proposal.accepted = True
    db.commit()
    return dump(strategy)

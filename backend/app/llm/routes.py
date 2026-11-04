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
from app.schemas.domain import StrictModel

router = APIRouter(prefix="/api/llm")


class AuthorRequest(StrictModel):
    strategy_id: str
    prompt: str = Field(min_length=1, max_length=5000)


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
    strategy.draft = proposal.config
    strategy.llm_metadata = proposal.metadata_json
    strategy.draft_revision += 1
    proposal.accepted = True
    db.commit()
    return dump(strategy)

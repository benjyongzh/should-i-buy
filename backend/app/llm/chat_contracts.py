"""Conversation output is research commentary, never historical signal data."""

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.domain import StrategyConfig, StrictModel


class ChatSelection(StrictModel):
    profile_id: str | None = None
    dataset_id: str | None = None
    strategy_input_ids: list[str] = Field(default_factory=list, max_length=20)
    run_ids: list[str] = Field(default_factory=list, max_length=5)
    study_ids: list[str] = Field(default_factory=list, max_length=5)
    as_of: AwareDatetime | None = None


class ChatRequest(StrictModel):
    request_id: str = Field(min_length=1, max_length=80)
    expected_revision: int = Field(ge=1)
    message: str = Field(min_length=1, max_length=5000)
    selection: ChatSelection = Field(default_factory=ChatSelection)


class Clarification(StrictModel):
    question: str = Field(min_length=1, max_length=500)
    choices: list[str] = Field(min_length=2, max_length=5)


class ResearchEstimate(StrictModel):
    estimate: str = Field(min_length=1, max_length=1000)
    horizon: str = Field(min_length=1, max_length=200)
    method: str = Field(min_length=1, max_length=1000)
    uncertainty: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[str] = Field(min_length=1, max_length=10)


class ChatReply(StrictModel):
    message: str = Field(min_length=1, max_length=6000)
    outcome: Literal["clarify", "discuss", "propose", "unsupported"]
    questions: list[Clarification] = Field(default_factory=list, max_length=5)
    estimates: list[ResearchEstimate] = Field(default_factory=list, max_length=5)
    cited_evidence_ids: list[str] = Field(default_factory=list, max_length=30)
    config: StrategyConfig | None = None
    assumptions: list[str] = Field(default_factory=list, max_length=20)
    data_requirements: list[str] = Field(default_factory=list, max_length=20)
    unsupported_requests: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def review_gate(self):
        if self.outcome == "clarify" and not self.questions:
            raise ValueError("clarification requires questions")
        if self.outcome == "propose":
            if self.config is None or self.questions or self.unsupported_requests:
                raise ValueError("a proposal requires supported rules with no unanswered questions")
        elif self.config is not None:
            raise ValueError("discussion/clarification cannot silently propose configuration")
        if self.questions and self.outcome != "clarify":
            raise ValueError("unanswered questions must remain a clarification")
        return self

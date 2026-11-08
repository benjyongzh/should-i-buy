from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.domain import StrictModel


class CollectionRequest(StrictModel):
    request_id: str = Field(min_length=1, max_length=80)
    start_year: int = Field(default=2018, ge=2012, le=2035)
    end_year: int = Field(default=2025, ge=2012, le=2035)
    chambers: list[Literal["house", "senate"]] = Field(
        default=["house", "senate"], min_length=1, max_length=2
    )
    supporting_years: list[int] = Field(default_factory=list, max_length=4)
    lookup_archives: bool = True
    acknowledge_personal_noncommercial_use: Literal[True]

    @model_validator(mode="after")
    def bounds(self):
        if self.start_year > self.end_year or self.end_year - self.start_year > 11:
            raise ValueError("use an ordered interval of at most12 index years")
        if len(set(self.chambers)) != len(self.chambers):
            raise ValueError("duplicate chamber")
        if len(set(self.supporting_years)) != len(self.supporting_years) or any(
            y < 2012 or y > datetime.now(UTC).year or self.start_year <= y <= self.end_year
            for y in self.supporting_years
        ):
            raise ValueError(
                "supporting indexes must be distinct historical years outside the main scope"
            )
        if self.end_year > datetime.now(UTC).year:
            raise ValueError("index interval cannot be in the future")
        return self

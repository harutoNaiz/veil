"""Request models for the opt-in routes: strict, no extra fields, bounded."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Bucket = Literal["0", "1-9", "10-99", "100+"]
Word = Annotated[str, StringConstraints(min_length=1, max_length=64)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Counts(_Strict):
    covers: Bucket | None = None
    peeks: Bucket | None = None
    corrections: Bucket | None = None
    packsInstalled: Bucket | None = None


class CompileRequest(_Strict):
    consent: Literal[True]
    words: Annotated[list[Word], Field(min_length=1, max_length=8)]


class MetricsRequest(_Strict):
    consent: Literal[True]
    day: Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    counts: Counts

    @field_validator("day")
    @classmethod
    def _real_date(cls, v: str) -> str:
        dt.date.fromisoformat(v)
        return v


class EvalRequest(_Strict):
    packId: Annotated[str, StringConstraints(min_length=1, max_length=64)]

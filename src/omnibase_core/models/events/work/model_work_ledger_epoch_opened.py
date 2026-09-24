# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Ledger-epoch-opened work event (OMN-16177, typed work ledger).

Tool-written, never hand-written. A cutover (epoch 0) or a roll closes the
previous ledger file into an archive and opens a new epoch. The event pins the
archive by repo-relative path, SHA-256 and line count, and names every event
carried forward into the new epoch (open claims, holds in force, unanswered
messages). A cutover also cites the review list its carried events came from.
"""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, field_validator, model_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkLedgerEpochOpened"]

_PATH_MAX_LENGTH = 512


class ModelWorkLedgerEpochOpened(ModelWorkEventBase):
    """A cutover or a roll opened a new ledger epoch."""

    kind: Literal[EnumWorkEventKind.LEDGER_EPOCH_OPENED] = Field(
        default=EnumWorkEventKind.LEDGER_EPOCH_OPENED, frozen=True
    )
    reason: Literal["cutover", "roll"] = Field(
        ..., description="Why the epoch opened: the one-time cutover, or a roll."
    )
    epoch_seq: int = Field(..., ge=0, description="Epoch number; the cutover is 0.")
    archived_path: str = Field(
        ...,
        min_length=1,
        max_length=_PATH_MAX_LENGTH,
        description="Repo-relative path of the archived previous ledger file.",
    )
    archived_sha256: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 of the archived file, lower-case hex.",
    )
    archived_line_count: int = Field(
        ..., ge=0, description="Line count of the archived file."
    )
    carried: tuple[uuid.UUID, ...] = Field(
        default=(),
        description="event_ids carried forward into the new epoch, each once.",
    )
    review_list_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=_PATH_MAX_LENGTH,
        description="The cutover review list the carried events came from. Required on a cutover.",
    )

    @field_validator("carried")
    @classmethod
    def _refuse_duplicate_carry(
        cls, raw: tuple[uuid.UUID, ...]
    ) -> tuple[uuid.UUID, ...]:
        """A carry list naming one event twice is a defect, not a set to collapse."""
        if len(set(raw)) != len(raw):
            raise ValueError("carried names the same event_id more than once")
        return raw

    @field_validator("archived_path")
    @classmethod
    def _repo_relative(cls, raw: str) -> str:
        path = PurePosixPath(raw)
        if not raw.strip() or path.is_absolute() or ".." in path.parts:
            raise ValueError(
                f"archived_path {raw!r} must be repo-relative, with no '..' part"
            )
        return raw

    @model_validator(mode="after")
    def _cutover_cites_its_review_list(self) -> ModelWorkLedgerEpochOpened:
        if self.reason == "cutover" and self.review_list_ref is None:
            raise ValueError("a cutover epoch must cite its review_list_ref")
        return self

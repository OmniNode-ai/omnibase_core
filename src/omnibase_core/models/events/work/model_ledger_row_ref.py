# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A reference to one row of the markdown work ledger (OMN-19620, plan T17).

Typed events sometimes have to name a row that exists only in the markdown
ledger: a question first asked as a legacy row and re-issued as a typed event,
or a legacy row cited as evidence. A line number alone moves when the ledger
rolls, so the reference also carries the row's own timestamp and lane. A reader
confirms that the line still holds that row before it trusts the reference,
which is the check the decisions register's roll geometry already makes.
"""

from __future__ import annotations

import re
from typing import Final

from pydantic import AwareDatetime, Field, field_validator

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase

__all__ = ["LEDGER_ROW_LANE_PATTERN", "ModelLedgerRowRef"]

LEDGER_ROW_LANE_PATTERN: Final[str] = r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
"""The row grammar's lane token (``ledger_grammar.LANE_TOKEN``)."""

_MD_PATH_RE: Final = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*\.md$")


class ModelLedgerRowRef(ModelEventPayloadBase):
    """One md ledger row, by repo-relative path, line, timestamp and lane. Hashable."""

    path: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description=(
            "Repo-relative path of the md ledger or archive split holding the row, "
            "e.g. 'docs/tracking/archive/ROLLING_WORK_LEDGER_2026-09-20-split.md'."
        ),
    )
    line: int = Field(..., ge=1, description="1-based line of the row in that file.")
    stamp: AwareDatetime = Field(
        ..., description="The row's own timestamp cell, so a moved line is detected."
    )
    lane: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=LEDGER_ROW_LANE_PATTERN,
        description="The row's lane cell, so a moved line is detected.",
    )

    @field_validator("path")
    @classmethod
    def _repo_relative_md(cls, raw: str) -> str:
        if _MD_PATH_RE.match(raw) is None or ".." in raw.split("/") or "//" in raw:
            raise ValueError(
                f"path {raw!r} must be a repo-relative .md path with no '..' segment "
                "and no leading '/'"
            )
        return raw

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The rule values of the action-pin check, read from an overlay file (OMN-17427)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.action_pins.model_action_pin_known_exception import (
    ModelActionPinKnownException,
)

__all__ = ["ModelActionPinOverlay"]


class ModelActionPinOverlay(BaseModel):
    """What counts as first-party and what a first-party ref must look like.

    Attributes:
        first_party_orgs: GitHub organisations whose repositories are first-party.
        tag_pattern: Regular expression a first-party ref must fully match
            (the dev-merge tag, ``dev-YYYYMMDDhhmmss-<sha12>``).
        first_party_main: ``fail`` refuses a first-party ``@main`` ref; ``warn``
            reports it as a finding to remove later (the pre-existing allowance).
        known_exceptions: First-party sha pins admitted with a reason.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    first_party_orgs: tuple[str, ...] = Field(min_length=1)
    tag_pattern: str = Field(min_length=1)
    first_party_main: Literal["fail", "warn"] = "fail"
    known_exceptions: tuple[ModelActionPinKnownException, ...] = Field(default=())

    @field_validator("tag_pattern")
    @classmethod
    def _compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(
                f"tag_pattern is not a valid regular expression: {exc}"
            ) from exc
        return value

    def is_first_party(self, action: str) -> bool:
        """True when ``action`` (``owner/repo[/path]``) belongs to a first-party org."""
        owner = action.split("/", 1)[0].casefold()
        return any(owner == org.casefold() for org in self.first_party_orgs)

    def matches_tag(self, ref: str) -> bool:
        """True when ``ref`` fully matches the overlay's tag pattern."""
        return re.fullmatch(self.tag_pattern, ref) is not None

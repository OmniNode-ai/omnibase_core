# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextSourceResult — a context source's answer (OMN-18531 / TC.1)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from omnibase_core.enums.enum_context_source_error_code import (
    EnumContextSourceErrorCode,
)
from omnibase_core.enums.enum_context_source_status import EnumContextSourceStatus
from omnibase_core.models.context.model_context_source_entry import (
    ModelContextSourceEntry,
)

__all__ = ["ModelContextSourceResult"]

_NO_ENTRY_STATUSES = frozenset(
    {
        EnumContextSourceStatus.UNRESOLVED,
        EnumContextSourceStatus.DENIED,
        EnumContextSourceStatus.UNAVAILABLE,
    }
)


class ModelContextSourceResult(BaseModel):
    """Entries plus the paging, count and timing fields the caller needs.

    The status and the entries must agree. ``RESOLVED`` carries at least one
    entry, so an empty read is never reported as resolved; ``UNRESOLVED``,
    ``DENIED`` and ``UNAVAILABLE`` carry none. A response that fails
    validation becomes ``UNAVAILABLE`` with an ``error_code`` (see
    ``from_raw_response``), never an empty ``RESOLVED``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    status: EnumContextSourceStatus
    entries: tuple[ModelContextSourceEntry, ...] = ()
    has_more: bool = False
    entry_counts: Mapping[str, int] = Field(
        default_factory=dict, description="Entries returned, keyed by source name"
    )
    leg_timings_ms: Mapping[str, int] = Field(
        default_factory=dict, description="Wall time per read leg, in milliseconds"
    )
    error_code: EnumContextSourceErrorCode | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def _status_agrees_with_entries(self) -> Self:
        if self.status is EnumContextSourceStatus.RESOLVED and not self.entries:
            raise ValueError("a RESOLVED result must carry at least one entry")
        if self.status in _NO_ENTRY_STATUSES and self.entries:
            raise ValueError(f"a {self.status.value} result must not carry entries")
        return self

    @model_validator(mode="after")
    def _error_is_typed_and_unavailable(self) -> Self:
        if self.error_code is None:
            if self.error_message is not None:
                raise ValueError("error_message requires error_code")
            return self
        if self.status is not EnumContextSourceStatus.UNAVAILABLE:
            raise ValueError("an error_code is only valid on an UNAVAILABLE result")
        return self

    @classmethod
    def error(cls, code: EnumContextSourceErrorCode, message: str) -> Self:
        """Typed error result: UNAVAILABLE, no entries, the code and the cause."""
        return cls(
            status=EnumContextSourceStatus.UNAVAILABLE,
            error_code=code,
            error_message=message,
        )

    @classmethod
    def from_raw_response(cls, raw: Mapping[str, object]) -> Self:
        """Validate an untyped response; a failure is an error result.

        The response side of the two-sided check: a source's raw reply that
        does not validate yields ``UNAVAILABLE`` with ``INVALID_RESPONSE``
        and the validation message, never an empty ``RESOLVED``.
        """
        try:
            return cls.model_validate(raw)
        except ValidationError as exc:
            return cls.error(EnumContextSourceErrorCode.INVALID_RESPONSE, str(exc))

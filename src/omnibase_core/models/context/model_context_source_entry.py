# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextSourceEntry — one piece of text a context source returns (OMN-18531 / TC.1)."""

from __future__ import annotations

import hashlib
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_context_factor import EnumContextFactor
from omnibase_core.enums.enum_context_source_status import EnumContextSourceStatus
from omnibase_core.enums.enum_context_supersession_status import (
    EnumContextSupersessionStatus,
)
from omnibase_core.models.context.model_context_source_span import (
    ModelContextSourceSpan,
)

__all__ = ["ModelContextSourceEntry"]


class ModelContextSourceEntry(BaseModel):
    """A text with its provenance, hash and verification flags.

    Two invariants hold at construction. The text must hash to ``text_sha256``
    (sha256 of its UTF-8 bytes, lowercase hex). An entry marked
    ``verbatim_verified`` must say where the text came from and which range
    of it (``source_ref`` and ``span``), and cannot also be a paraphrase.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    factor: EnumContextFactor
    text: str
    source_ref: str | None = Field(
        default=None, min_length=1, description="Where the text came from"
    )
    span: ModelContextSourceSpan | None = None
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: EnumContextSourceStatus
    supersession_status: EnumContextSupersessionStatus = (
        EnumContextSupersessionStatus.UNKNOWN
    )
    verbatim_verified: bool = False
    paraphrase: bool = False
    as_of: datetime = Field(
        description="Timestamp of the source state the text is from"
    )

    @model_validator(mode="after")
    def _text_matches_hash(self) -> ModelContextSourceEntry:
        actual = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        if actual != self.text_sha256:
            raise ValueError(
                f"text_sha256 {self.text_sha256} does not match the sha256 of text ({actual})"
            )
        return self

    @model_validator(mode="after")
    def _verbatim_names_its_source(self) -> ModelContextSourceEntry:
        if not self.verbatim_verified:
            return self
        if self.source_ref is None or self.span is None:
            raise ValueError("verbatim_verified requires both source_ref and span")
        if self.paraphrase:
            raise ValueError(
                "an entry cannot be both verbatim_verified and a paraphrase"
            )
        return self

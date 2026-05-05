# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelTicketFilter — scope predicate filter targeting the current Linear ticket namespace."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelTicketFilter(BaseModel):
    """Predicate filter targeting the current Linear ticket namespace."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    namespace: str = Field(
        description=(
            "Linear ticket namespace prefix (e.g. 'OMN'). "
            "Matched against the active ticket context when available."
        )
    )


__all__ = ["ModelTicketFilter"]

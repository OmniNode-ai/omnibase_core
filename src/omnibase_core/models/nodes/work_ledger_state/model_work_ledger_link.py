# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One valid relationship link of the work-ledger fold (OMN-21107, TA.5)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_work_ledger_relation import EnumWorkLedgerRelation

__all__ = ["ModelWorkLedgerLink"]


class ModelWorkLedgerLink(BaseModel):
    """A typed relationship one work event declares about an earlier one.

    Only a link whose target exists — and, for supersedes, amends and extends,
    whose target is a ruling or a consent — lands here. A refused reference
    creates no link; it is listed as a ``ModelInvalidRelationshipRef`` instead.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source: uuid.UUID = Field(..., description="The event_id holding the reference.")
    target: uuid.UUID = Field(..., description="The event_id it names.")
    relation: EnumWorkLedgerRelation = Field(..., description="How it relates to it.")
    operator_span: str | None = Field(
        default=None,
        description=(
            "On a CORRECTS link: the exact span of the operator's words the "
            "correction concerns. Never read by a checker."
        ),
    )

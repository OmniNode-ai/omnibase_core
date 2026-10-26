# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A relationship reference the work-ledger fold refused (OMN-21107, TA.5)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_invalid_relationship_reason import (
    EnumInvalidRelationshipReason,
)
from omnibase_core.enums.enum_work_ledger_relation import EnumWorkLedgerRelation

__all__ = ["ModelInvalidRelationshipRef"]


class ModelInvalidRelationshipRef(BaseModel):
    """A supersedes, amends, extends or corrects reference that names nothing
    usable, and why."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    referrer: uuid.UUID = Field(..., description="The event_id holding the reference.")
    target: uuid.UUID = Field(..., description="The event_id it names.")
    relation: EnumWorkLedgerRelation = Field(
        ..., description="The relation the reference declared."
    )
    reason: EnumInvalidRelationshipReason = Field(
        ..., description="Why it was refused."
    )

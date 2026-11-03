# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reply to one contract load request (OMN-21226)."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_hotload_reason import EnumContractHotloadReason
from omnibase_core.enums.enum_contract_load_outcome import EnumContractLoadOutcome

__all__ = ["ModelContractLoadReply"]


class ModelContractLoadReply(BaseModel):
    """One reply per request: accepted, rejected, unchanged or replayed.

    Attributes:
        entity_id: Identifies the sender principal and the request id together, so
            one request has one reply.
        outcome: How the registry answered.
        reason: Typed reason; ``none`` when the outcome needs none.
        registry_version: The registry version the answer is about.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entity_id: str = Field(min_length=1)
    outcome: EnumContractLoadOutcome
    reason: EnumContractHotloadReason
    registry_version: int = Field(ge=0)

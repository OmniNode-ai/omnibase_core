# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime event: one registry change applied (or not) by one runtime (OMN-21226)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_hotload_applied_status import (
    EnumContractHotloadAppliedStatus,
)
from omnibase_core.enums.enum_contract_hotload_operation import (
    EnumContractHotloadOperation,
)
from omnibase_core.enums.enum_contract_hotload_reason import EnumContractHotloadReason

__all__ = ["ModelContractHotloadApplied"]


class ModelContractHotloadApplied(BaseModel):
    """What one runtime instance did with one registry change.

    Attributes:
        entity_id: The contract name.
        registry_version: The registry version the runtime acted on.
        content_hash: Canonical content hash of the contract acted on.
        operation: The operation the runtime applied or refused.
        status: ``applied``, ``refused`` or ``failed``.
        reason: Typed reason; ``none`` when the status needs none.
        runtime_instance_id: The runtime instance.
        incarnation_id: The incarnation of that instance (changes on restart).
        profile: The runtime profile.
        lane: The lane the runtime serves.
        image_digest: Digest of the image the runtime runs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entity_id: str = Field(min_length=1)
    registry_version: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation: EnumContractHotloadOperation
    status: EnumContractHotloadAppliedStatus
    reason: EnumContractHotloadReason
    runtime_instance_id: UUID
    incarnation_id: UUID
    profile: str = Field(min_length=1)
    lane: str = Field(min_length=1)
    image_digest: str = Field(min_length=1)

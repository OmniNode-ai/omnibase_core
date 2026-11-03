# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime event: one registry change applied (or not) by one runtime (OMN-21226)."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_contract_hotload_operation import (
    EnumContractHotloadOperation,
)
from omnibase_core.enums.enum_contract_hotload_reason import EnumContractHotloadReason
from omnibase_core.enums.enum_contract_hotload_status import EnumContractHotloadStatus

__all__ = ["ModelContractHotloadApplied"]


class ModelContractHotloadApplied(BaseModel):
    """What one runtime instance did with one registry change.

    Attributes:
        entity_id: The contract name.
        registry_version: The registry version the runtime acted on.
        content_hash: Canonical content hash of the contract acted on.
        operation: The operation the runtime applied or refused.
        status: ``materialized``, ``adopted``, ``replaced``, ``removed``,
            ``refused``, ``not_ready`` or ``failed``.
        reason: Typed reason, or ``None``. A ``refused`` event must carry one.
        runtime_instance_id: The runtime instance.
        incarnation_id: The incarnation of that instance (fresh at each process start).
        profile: The runtime profile.
        lane: The lane the runtime serves.
        image_digest: Digest of the image the runtime runs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entity_id: str = Field(min_length=1)
    registry_version: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation: EnumContractHotloadOperation
    status: EnumContractHotloadStatus
    reason: EnumContractHotloadReason | None
    runtime_instance_id: UUID
    incarnation_id: UUID
    profile: str = Field(min_length=1)
    lane: str = Field(min_length=1)
    image_digest: str = Field(min_length=1)

    @model_validator(mode="after")
    def _a_refusal_names_its_reason(self) -> Self:
        if self.status is EnumContractHotloadStatus.REFUSED and self.reason is None:
            raise ValueError("a refused event must carry a reason")
        return self

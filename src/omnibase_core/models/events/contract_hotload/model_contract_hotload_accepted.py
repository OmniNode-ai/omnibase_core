# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Registry state: a contract the registry has accepted (OMN-21226)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_hotload_operation import (
    EnumContractHotloadOperation,
)

__all__ = ["ModelContractHotloadAccepted"]


class ModelContractHotloadAccepted(BaseModel):
    """The compacted record of one accepted contract, keyed by its name.

    Attributes:
        entity_id: The contract name (the record's compaction key).
        registry_version: The registry version this acceptance created.
        content_hash: Canonical content hash of the installed contract.
        operation: The operation that was accepted.
        owner: The principal that owns the registration.
        registration_request_id: The request this acceptance answers.
        contract_yaml: The installed contract, as text.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entity_id: str = Field(min_length=1)
    registry_version: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation: EnumContractHotloadOperation
    owner: str = Field(min_length=1)
    registration_request_id: UUID
    contract_yaml: str = Field(min_length=1)

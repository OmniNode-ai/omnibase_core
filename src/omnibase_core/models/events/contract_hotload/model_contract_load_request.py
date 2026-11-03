# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Request to load or remove one installed contract (OMN-21226)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_hotload_operation import (
    EnumContractHotloadOperation,
)

__all__ = ["ModelContractLoadRequest"]


class ModelContractLoadRequest(BaseModel):
    """A caller asks the registry to load or remove one contract by name and hash.

    Attributes:
        operation: ``load`` or ``remove``.
        contract_name: The installed contract's name.
        content_hash: Canonical content hash of the contract the caller means.
        registration_request_id: Caller-chosen id; the reply and the registry
            record carry it back, so a resend is told from a new request.
        expected_version: The registry version the caller last saw for the name
            (``0`` for a name it has never seen); a mismatch is a conflict.
        owner: The principal that owns the registration.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    operation: EnumContractHotloadOperation
    contract_name: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    registration_request_id: UUID
    expected_version: int = Field(ge=0)
    owner: str = Field(min_length=1)

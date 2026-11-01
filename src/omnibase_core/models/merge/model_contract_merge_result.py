# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract merge result with applied overlay references and deterministic hashes.

A ModelContractMergeResult carries the expanded contract, the overlays in
application order, and the resolver configuration and effective contract hashes.

See Also:
    - OMN-21506: Resolver configuration and effective contract hashes
    - ModelOverlayRef: Record of a single applied overlay
    - ContractMergeEngine: Produces the merge result
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.merge.model_overlay_ref import ModelOverlayRef


class ModelContractMergeResult(BaseModel):
    """
    Immutable result of resolving a contract patch and its overlay stack.

    Attributes:
        contract: Expanded handler contract after all overlays are applied.
        overlay_refs: Applied overlays in application order.
        resolver_config_hash: Hash of the profile, node type, and overlay refs.
        effective_contract_hash: Hash of the expanded handler contract.

    See Also:
        - OMN-21506: Resolver configuration and effective contract hashes
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract: ModelHandlerContract = Field(
        ...,
        description="Expanded handler contract after all overlays are applied.",
    )

    overlay_refs: list[ModelOverlayRef] = Field(
        default_factory=list,
        description="Applied overlays in application order.",
    )

    resolver_config_hash: str = Field(
        ...,
        min_length=1,
        description="Canonical JSON SHA256 hash of the resolver configuration.",
    )

    effective_contract_hash: str = Field(
        ...,
        min_length=1,
        description="Canonical JSON SHA256 hash of the effective contract.",
    )


__all__ = ["ModelContractMergeResult"]

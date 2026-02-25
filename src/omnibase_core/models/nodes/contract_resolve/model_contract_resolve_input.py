# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input models for the contract.resolve compute node.

Defines the typed input surface for NodeContractResolveCompute — the
canonical overlay resolution interface for the ONEX platform.

.. versionadded:: OMN-2754
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference

__all__ = [
    "ModelContractResolveInput",
    "ModelContractResolveOptions",
]


class ModelContractResolveOptions(BaseModel):
    """Behavioural flags controlling what the resolve node computes.

    Attributes:
        include_diff: When ``True``, the resolved output will contain a
            human-readable unified diff showing what changed from base to
            resolved contract.
        include_overlay_refs: When ``True``, each applied patch is reflected
            as a :class:`ModelOverlayRef` in the output, enabling audit trails.
        normalize_for_hash: When ``True``, the resolved contract is normalised
            (None fields stripped, keys sorted) before the canonical hash is
            computed. Should almost always be ``True`` in production.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    include_diff: bool = Field(
        default=False,
        description="Include unified diff from base to resolved contract.",
    )

    include_overlay_refs: bool = Field(
        default=True,
        description="Populate overlay_refs in the output with per-patch metadata.",
    )

    normalize_for_hash: bool = Field(
        default=True,
        description=(
            "Strip None fields and sort keys before hashing "
            "(RFC 8785 compatible canonical form)."
        ),
    )


class ModelContractResolveInput(BaseModel):
    """Input to the contract.resolve compute node.

    The node merges ``patches`` sequentially onto ``base_profile_ref``,
    applying each patch in list order (lowest-first). The result is a fully
    expanded :class:`~omnibase_core.models.contracts.model_handler_contract.ModelHandlerContract`
    with a content-addressed hash.

    Attributes:
        base_profile_ref: The base profile to resolve from. This is the
            starting point before any patch is applied.
        patches: Ordered list of contract patches to apply. Applied sequentially
            from index 0 (lowest precedence) to ``len(patches) - 1`` (highest).
            An empty list resolves the base profile without modification.
        options: Flags controlling what additional data the node computes.

    Example:
        >>> from omnibase_core.models.nodes.contract_resolve import (
        ...     ModelContractResolveInput,
        ...     ModelContractResolveOptions,
        ... )
        >>> from omnibase_core.models.contracts.model_profile_reference import (
        ...     ModelProfileReference,
        ... )
        >>> inp = ModelContractResolveInput(
        ...     base_profile_ref=ModelProfileReference(
        ...         profile="compute_pure", version="1.0.0"
        ...     ),
        ...     patches=[],
        ...     options=ModelContractResolveOptions(include_diff=False),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    base_profile_ref: ModelProfileReference = Field(
        ...,
        description=(
            "Reference to the base profile that anchors the resolution chain. "
            "All patches in ``patches`` extend this profile."
        ),
    )

    patches: list[ModelContractPatch] = Field(
        default_factory=list,
        description=(
            "Ordered list of contract patches to apply. "
            "Applied sequentially, lowest index first. "
            "An empty list resolves the base profile without modification."
        ),
    )

    options: ModelContractResolveOptions = Field(
        default_factory=ModelContractResolveOptions,
        description="Behavioural flags for the resolve operation.",
    )

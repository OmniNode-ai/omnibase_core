# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Overlay stack entry model for multi-patch merge pipeline.

A ModelOverlayStackEntry encapsulates a single overlay in the ordered list
that is passed to :class:`ContractMergeEngine.merge_with_overlays`. Entries
are applied sequentially in list order. The ``scope`` field declares the
precedence tier; if overlays are supplied out of canonical scope order a
warning is logged and they are sorted to canonical order (unless
``strict_ordering=True`` is set on the engine call).

See Also:
    - OMN-2757: Overlay stacking — multi-patch pipeline
    - EnumOverlayScope: Scope precedence tiers
    - ModelOverlayRef: Lightweight record produced after applying an entry
    - ContractMergeEngine: Engine that consumes ordered stacks

.. versionadded:: 0.18.0
    Added as part of overlay stacking pipeline (OMN-2757)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch


class ModelOverlayStackEntry(BaseModel):
    """
    A single overlay in an ordered multi-patch stack.

    Ordered lists of this model are the canonical input to the overlay
    stacking pipeline in :meth:`ContractMergeEngine.merge_with_overlays`.

    Attributes:
        overlay_id: Stable identifier for this overlay.
        overlay_patch: The contract patch to apply for this overlay.
        scope: Precedence tier of this overlay.
        version: Semantic version of this overlay.
        source_ref: Optional provenance reference (e.g. a git SHA or S3 URI).

    Example:
        >>> from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
        >>> from omnibase_core.models.merge.model_overlay_stack_entry import (
        ...     ModelOverlayStackEntry,
        ... )
        >>> from omnibase_core.models.contracts.model_contract_patch import (
        ...     ModelContractPatch,
        ... )
        >>>
        >>> entry = ModelOverlayStackEntry(
        ...     overlay_id="org-defaults",
        ...     overlay_patch=patch,
        ...     scope=EnumOverlayScope.ORG,
        ...     version="1.0.0",
        ... )

    .. versionadded:: 0.18.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overlay_id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier for this overlay (slug or UUID).",
    )

    overlay_patch: ModelContractPatch = Field(
        ...,
        description="The contract patch applied by this overlay.",
    )

    scope: EnumOverlayScope = Field(
        ...,
        description="Precedence tier of this overlay.",
    )

    version: str = Field(
        default="1.0.0",
        min_length=1,
        description="Semantic version of this overlay.",
    )

    source_ref: str | None = Field(
        default=None,
        description="Optional provenance reference (git SHA, S3 URI, etc.).",
    )


__all__ = ["ModelOverlayStackEntry"]

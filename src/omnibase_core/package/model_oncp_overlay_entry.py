# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ONCP overlay entry model.

Defines the manifest entry for a single overlay included in a ``.oncp`` package.

See Also:
    - OMN-2758: Phase 5 — .oncp contract package MVP
    - OMN-2754: ``compute_canonical_hash`` canonical hash utility

.. versionadded:: 0.19.0
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope

__all__ = ["ModelOncpOverlayEntry"]


class ModelOncpOverlayEntry(BaseModel):
    """Manifest entry describing a single overlay included in the package.

    Each entry maps one :class:`~omnibase_core.models.contracts.model_contract_patch.ModelContractPatch`
    to its position in the overlay stack plus a content hash for integrity
    verification at ``open``-time.

    Attributes:
        overlay_id: Stable identifier for the overlay (slug or UUID).
        scope: Precedence tier at which the overlay is applied.
        path: Relative path inside the zip (e.g. ``overlays/my_patch.overlay.yaml``).
        content_hash: SHA-256 hex digest of the serialised overlay YAML.
        order_index: Zero-based position in the application order.

    .. versionadded:: 0.19.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: overlay IDs are human-readable slugs, not database UUIDs
    overlay_id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier for this overlay (slug or UUID).",
    )
    scope: EnumOverlayScope = Field(
        ...,
        description="Precedence tier at which this overlay is applied.",
    )
    path: str = Field(
        ...,
        min_length=1,
        description="Relative path inside the zip archive.",
    )
    content_hash: str = Field(
        ...,
        min_length=1,
        description="SHA-256 hex digest of the serialised overlay YAML content.",
    )
    order_index: int = Field(
        ...,
        ge=0,
        description="Zero-based position in the ordered application stack.",
    )

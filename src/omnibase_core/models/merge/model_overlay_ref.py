# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Overlay reference model for contract merge events.

A ModelOverlayRef is a lightweight, immutable record describing a single
overlay that was applied during a merge operation. It is collected into the
``overlay_refs`` list that is emitted on merge-completed events so consumers
can audit the full overlay stack without re-loading the overlay content.

See Also:
    - OMN-2757: Overlay stacking — multi-patch pipeline
    - ModelOverlayStackEntry: The input model that produces a ModelOverlayRef
    - ModelContractMergeCompletedEvent: Consumes overlay_refs list

.. versionadded:: 0.18.0
    Added as part of overlay stacking pipeline (OMN-2757)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope


class ModelOverlayRef(BaseModel):
    """
    Immutable record of a single overlay applied during a merge.

    Emitted in the ``overlay_refs`` list on merge-completed events. Each
    entry corresponds to one :class:`ModelOverlayStackEntry` that was
    processed, in ascending order of application (``order_index`` 0-based).

    Attributes:
        overlay_id: Stable identifier for the overlay (e.g. a slug or UUID).
        version: Semantic version string of the overlay at time of application.
        content_hash: Content-addressed hash of the overlay patch, if computed.
            ``None`` when hashing is not performed.
        scope: The :class:`EnumOverlayScope` tier this overlay belongs to.
        order_index: Zero-based position in the ordered stack that was applied.

    Example:
        >>> from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
        >>> from omnibase_core.models.merge.model_overlay_ref import ModelOverlayRef
        >>>
        >>> ref = ModelOverlayRef(
        ...     overlay_id="org-defaults",
        ...     version="1.2.0",
        ...     content_hash="sha256:abc123",
        ...     scope=EnumOverlayScope.ORG,
        ...     order_index=0,
        ... )
        >>> ref.overlay_id
        'org-defaults'

    .. versionadded:: 0.18.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overlay_id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier for this overlay (slug or UUID).",
    )

    version: str = Field(
        ...,
        min_length=1,
        description="Semantic version of the overlay at time of application.",
    )

    content_hash: str | None = Field(
        default=None,
        description="Content-addressed hash of the overlay patch. "
        "None when hashing is not performed.",
    )

    scope: EnumOverlayScope = Field(
        ...,
        description="Precedence tier this overlay belongs to.",
    )

    order_index: int = Field(
        ...,
        ge=0,
        description="Zero-based position in the ordered application stack.",
    )


__all__ = ["ModelOverlayRef"]

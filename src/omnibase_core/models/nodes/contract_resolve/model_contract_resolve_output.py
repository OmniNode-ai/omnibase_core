# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output models for the contract.resolve compute node.

Defines the typed output surface for NodeContractResolveCompute, including
per-patch overlay references and resolver build metadata.

.. versionadded:: OMN-2754
"""

from __future__ import annotations

from importlib.metadata import version as pkg_version

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract

__all__ = [
    "ModelContractResolveOutput",
    "ModelOverlayRef",
    "ModelResolverBuild",
]

# ─────────────────────────────────────────────────────────────────────────────
# Package version helper
# ─────────────────────────────────────────────────────────────────────────────


def _omnibase_core_version() -> str:
    """Return the installed omnibase_core package version, or 'unknown'."""
    try:
        return pkg_version("omnibase_core")
    except Exception:  # fallback-ok: version probe is best-effort
        return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Supporting models
# ─────────────────────────────────────────────────────────────────────────────


class ModelOverlayRef(BaseModel):
    """Reference to a single overlay that was applied during resolution.

    Each entry corresponds to one patch from
    :attr:`ModelContractResolveInput.patches`, preserving the metadata needed
    for audit trails and content-addressed caching.

    Attributes:
        overlay_id: Stable identifier for the overlay (e.g. patch name or UUID).
        version: Semantic version of the overlay at the time of application.
        content_hash: SHA-256 of the canonical patch JSON — enables caching
            and integrity verification.
        source_ref: Optional human-readable reference to the patch source
            (e.g. a git commit, filename, or URL).
        scope: The resolution scope this overlay belongs to.
        order_index: Zero-based position in the patch application chain.
            Lower values were applied first (lower precedence).

    Example:
        >>> ref = ModelOverlayRef(
        ...     overlay_id="my_org_patch",
        ...     version="1.2.0",
        ...     content_hash="abc123...",
        ...     scope=EnumOverlayScope.ORG,
        ...     order_index=0,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overlay_id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier for the overlay.",
    )

    version: str = Field(
        ...,
        min_length=1,
        description="Semantic version of the overlay.",
    )

    content_hash: str = Field(
        ...,
        min_length=1,
        description="SHA-256 hex digest of the canonical patch JSON.",
    )

    source_ref: str | None = Field(
        default=None,
        description="Optional reference to the overlay source (git ref, filename, URL).",
    )

    scope: EnumOverlayScope = Field(
        default=EnumOverlayScope.PROJECT,
        description="Resolution scope for this overlay.",
    )

    order_index: int = Field(
        ...,
        ge=0,
        description=(
            "Zero-based position in the patch application chain. "
            "Lower values have lower precedence."
        ),
    )


class ModelResolverBuild(BaseModel):
    """Build metadata for the resolver that produced a resolved contract.

    Captured at resolution time so that cached resolved contracts can be
    invalidated when the resolver version changes.

    Attributes:
        core_version: Version of ``omnibase_core`` used during resolution.
        node_version: Version string of the NodeContractResolveCompute node.
        build_hash: SHA-256 of the resolver configuration canonical JSON.
            Used to detect resolver config drift between cache hits.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    core_version: str = Field(
        default_factory=_omnibase_core_version,
        description="Installed version of omnibase_core.",
    )

    node_version: str = Field(
        default="1.0.0",
        description="Version of the NodeContractResolveCompute node.",
    )

    build_hash: str = Field(
        ...,
        min_length=1,
        description="SHA-256 of the canonical resolver configuration.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Primary output model
# ─────────────────────────────────────────────────────────────────────────────


class ModelContractResolveOutput(BaseModel):
    """Output from the contract.resolve compute node.

    Contains the fully expanded, content-addressed contract along with
    per-patch hashes, overlay references, an optional diff, and resolver
    build metadata.

    Attributes:
        resolved_contract: The fully merged :class:`ModelHandlerContract`.
        resolved_hash: SHA-256 of the canonical JSON of ``resolved_contract``.
        patch_hashes: Per-patch SHA-256 hashes in application order (index 0
            corresponds to the first patch applied).
        overlay_refs: Structured metadata for each applied overlay. Present
            only when ``ModelContractResolveOptions.include_overlay_refs`` was
            ``True``. This is the first ticket to wire these as non-stubs.
        diff: Unified diff from the base contract to the resolved contract.
            ``None`` when ``ModelContractResolveOptions.include_diff`` was
            ``False``.
        resolver_build: Version and config metadata for the resolver.

    Example:
        >>> output = ModelContractResolveOutput(
        ...     resolved_contract=contract,
        ...     resolved_hash="abc...",
        ...     patch_hashes=["def..."],
        ...     overlay_refs=[],
        ...     diff=None,
        ...     resolver_build=ModelResolverBuild(build_hash="xyz..."),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    resolved_contract: ModelHandlerContract = Field(
        ...,
        description="Fully merged handler contract.",
    )

    resolved_hash: str = Field(
        ...,
        min_length=1,
        description="SHA-256 hex digest of the canonical resolved contract JSON.",
    )

    patch_hashes: list[str] = Field(
        default_factory=list,
        description=(
            "SHA-256 hash per patch in application order. "
            "Index 0 = first patch applied (lowest precedence)."
        ),
    )

    overlay_refs: list[ModelOverlayRef] = Field(
        default_factory=list,
        description=(
            "Per-overlay metadata for each applied patch. "
            "Empty when include_overlay_refs=False."
        ),
    )

    diff: str | None = Field(
        default=None,
        description=(
            "Unified diff from base to resolved contract. None when include_diff=False."
        ),
    )

    resolver_build: ModelResolverBuild = Field(
        ...,
        description="Build and version metadata for the resolver.",
    )

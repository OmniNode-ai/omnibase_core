# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ONCP manifest model.

Defines the top-level Pydantic model that corresponds to ``manifest.yaml``
inside a ``.oncp`` zip bundle. The manifest is the authoritative index of
a package: it records the resolved contract hash, per-overlay content hashes,
and scenario / invariant inventory.

All content hashes are computed via ``compute_canonical_hash()`` from
OMN-2754, ensuring RFC 8785-compatible deterministic serialisation.

See Also:
    - OMN-2758: Phase 5 — .oncp contract package MVP
    - OMN-2754: ``compute_canonical_hash`` canonical hash utility

.. versionadded:: 0.19.0
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.package.model_oncp_invariant_entry import ModelOncpInvariantEntry
from omnibase_core.package.model_oncp_overlay_entry import ModelOncpOverlayEntry
from omnibase_core.package.model_oncp_scenario_entry import ModelOncpScenarioEntry

__all__ = ["ModelOncpManifest", "MANIFEST_VERSION"]

# Manifest format version — increment when schema changes incompatibly.
MANIFEST_VERSION: int = 1


class ModelOncpManifest(BaseModel):
    """Top-level manifest model for a ``.oncp`` contract package.

    The manifest is serialised to ``manifest.yaml`` at the root of the zip
    archive and serves as the authoritative index of the package. All content
    hashes are computed via ``compute_canonical_hash()``.

    The ``resolved_contract_hash`` field captures the SHA-256 digest of the
    *fully-resolved* contract after all overlays have been stacked. Two
    packages with identical inputs must produce identical manifest hashes
    (determinism guarantee).

    Attributes:
        manifest_version: Schema version of the manifest format.
        package_id: Reverse-dotted identifier for the package.
        package_version: SemVer string for the package release.
        base_profile_ref: Name of the base profile extended by the overlays.
        base_profile_version: SemVer string of the base profile.
        base_profile_hash: Content hash of the base profile at pack time.
        omnibase_core_version: Version of omnibase_core used to build the
            package; pinned at build time from package metadata.
        overlays: Ordered list of overlay entries.
        resolved_contract_hash: SHA-256 hex digest of the fully-resolved
            contract produced by stacking all overlays.
        scenarios: Optional list of scenario entries.
        invariants: Optional list of invariant suite entries.

    Example:
        >>> manifest = ModelOncpManifest(
        ...     package_id="omninode.effects.http_fetch",
        ...     package_version="1.2.0",
        ...     base_profile_ref="effect_idempotent",
        ...     base_profile_version="1.0.0",
        ...     base_profile_hash="sha256:abc123",
        ...     omnibase_core_version="0.19.0",
        ...     overlays=[],
        ...     resolved_contract_hash="sha256:def456",
        ... )

    .. versionadded:: 0.19.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    manifest_version: int = Field(
        default=MANIFEST_VERSION,
        ge=1,
        description="Schema version of the manifest format.",
    )
    # string-id-ok: package IDs are reverse-dotted names (e.g. omninode.effects.http_fetch), not UUIDs
    package_id: str = Field(
        ...,
        min_length=1,
        description="Reverse-dotted identifier for the package.",
    )
    # string-version-ok: human-readable SemVer string embedded in content-addressed bundle
    package_version: str = Field(
        ...,
        min_length=1,
        description="SemVer string for the package release.",
    )
    # string-id-ok: base profile references are human-readable names, not UUIDs
    base_profile_ref: str = Field(
        ...,
        min_length=1,
        description="Name of the base profile extended by the overlays.",
    )
    # string-version-ok: base profile SemVer stored as string for content-addressed hashing
    base_profile_version: str = Field(
        ...,
        min_length=1,
        description="SemVer string of the base profile.",
    )
    base_profile_hash: str = Field(
        ...,
        min_length=1,
        description="Content hash of the base profile at pack time.",
    )
    # string-version-ok: pinned runtime version string from package metadata, not ModelSemVer
    omnibase_core_version: str = Field(
        ...,
        min_length=1,
        description="Version of omnibase_core used to build the package.",
    )
    overlays: list[ModelOncpOverlayEntry] = Field(
        default_factory=list,
        description="Ordered list of overlay entries in application order.",
    )
    resolved_contract_hash: str = Field(
        ...,
        min_length=1,
        description=(
            "SHA-256 hex digest of the fully-resolved contract after all "
            "overlays have been applied."
        ),
    )
    scenarios: list[ModelOncpScenarioEntry] = Field(
        default_factory=list,
        description="Scenario entries bundled in the package.",
    )
    invariants: list[ModelOncpInvariantEntry] = Field(
        default_factory=list,
        description="Invariant suite entries bundled in the package.",
    )

"""
Artifact Reference Model.

This module provides an opaque reference model for artifacts in the ONEX framework.
An artifact reference is a stable identifier that can be resolved through a registry,
rather than containing inline schema or content.

The reference model is intentionally minimal and opaque. The ``ref`` field serves as
the primary identifier, with optional fields for versioning, integrity verification,
and source tracking. The actual artifact content is resolved at runtime through
the registry system.

Location:
    ``omnibase_core.models.handlers.model_artifact_ref.ModelArtifactRef``

Import Example:
    .. code-block:: python

        from omnibase_core.models.handlers.model_artifact_ref import ModelArtifactRef
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        # Minimal reference (required field only)
        ref = ModelArtifactRef(ref="artifact://schemas/user-profile")

        # Full reference with all optional fields
        ref = ModelArtifactRef(
            ref="artifact://schemas/user-profile",
            digest="sha256:a1b2c3d4e5f6...",
            version=ModelSemVer(major=1, minor=2, patch=0),
            source="https://registry.omninode.ai/artifacts",
        )

        # Access fields
        print(ref.ref)       # "artifact://schemas/user-profile"
        print(ref.digest)    # "sha256:a1b2c3d4e5f6..."
        print(ref.version)   # ModelSemVer(major=1, minor=2, patch=0)

Design Notes:
    - **Opaque Identifier**: The ``ref`` field is intentionally opaque. Its format
      is determined by the registry implementation and may vary (URIs, URNs, paths).
    - **Registry Resolution**: This model does NOT contain inline content. The
      artifact content is resolved through a registry lookup using the ``ref``.
    - **Immutable**: The model is frozen to ensure references cannot be modified
      after creation.
    - **Extensible**: Future versions may add fields without breaking compatibility
      by using ``extra="forbid"`` to catch invalid field additions early.

See Also:
    - :class:`~omnibase_core.models.contracts.model_node_ref.ModelNodeRef`:
      Similar minimal reference pattern for nodes
    - :class:`~omnibase_core.models.core.model_contract_reference.ModelContractReference`:
      Contract reference pattern with path resolution

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1086 handler model additions.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelArtifactRef(BaseModel):
    """
    Opaque reference to an artifact in the ONEX framework.

    This model provides a registry-resolved reference to artifacts, enabling
    decoupled artifact management without inline content. The reference is
    resolved at runtime through the registry system.

    The model is immutable (frozen) to ensure reference stability after creation.

    Attributes:
        ref: Opaque stable identifier for the artifact. This is the primary
            key used for registry resolution. Format is registry-dependent
            (e.g., URI, URN, path, or custom identifier).
        digest: Optional content digest/checksum for integrity verification.
            Typically in the format "algorithm:hash" (e.g., "sha256:abc123...").
        version: Optional semantic version of the artifact.
        source: Optional source location or registry URL where the artifact
            can be retrieved.

    Example:
        >>> # Minimal reference
        >>> ref = ModelArtifactRef(ref="artifact://myartifact")
        >>> ref.ref
        'artifact://myartifact'

        >>> # Reference with version
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>> ref = ModelArtifactRef(
        ...     ref="artifact://myartifact",
        ...     version=ModelSemVer(major=2, minor=0, patch=0),
        ... )
        >>> str(ref.version)
        '2.0.0'

        >>> # Full reference
        >>> ref = ModelArtifactRef(
        ...     ref="artifact://schemas/event-envelope",
        ...     digest="sha256:e3b0c44298fc1c149afbf4c8996fb924",
        ...     version=ModelSemVer(major=1, minor=0, patch=0),
        ...     source="https://registry.example.com",
        ... )

    Note:
        This is an opaque reference. The actual artifact content must be
        resolved through a registry lookup using the ``ref`` identifier.
        The model does not validate the format of the ``ref`` field, as
        this is registry-specific.

    .. versionadded:: 0.4.0
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers)
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ref: str = Field(
        ...,
        description="Opaque stable identifier for the artifact. Used as the primary "
        "key for registry resolution. Format is registry-dependent.",
        min_length=1,
    )

    digest: str | None = Field(
        default=None,
        description="Optional content digest/checksum for integrity verification. "
        "Typically in format 'algorithm:hash' (e.g., 'sha256:abc123...').",
    )

    version: ModelSemVer | None = Field(
        default=None,
        description="Optional semantic version of the artifact.",
    )

    source: str | None = Field(
        default=None,
        description="Optional source location or registry URL where the artifact "
        "can be retrieved.",
    )

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        parts = [f"ref={self.ref!r}"]
        if self.version:
            parts.append(f"version={self.version}")
        return f"ModelArtifactRef({', '.join(parts)})"


__all__ = ["ModelArtifactRef"]

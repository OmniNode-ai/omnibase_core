"""
Packaging Metadata Reference Model.

This module provides an opaque reference model for packaging metadata configuration.
The reference acts as a stable identifier that is resolved at runtime to retrieve
the actual packaging configuration from a registry or resolver.

Packaging metadata encompasses all distribution and deployment configuration:
    - Import paths: Python module paths for node discovery and loading
    - Artifact locations: Registry URLs, file paths, or container images
    - Dependencies: Required packages, version constraints, and peer dependencies
    - Build configuration: Entry points, extras, and optional features
    - Distribution metadata: Package name, author, license, classifiers

Design Principles:
    - Opaque by design: The ref string format is intentionally unspecified to allow
      flexibility in registry implementations (URIs, UUIDs, slugs, etc.)
    - Immutable: Once created, references cannot be modified (frozen model)
    - Lightweight: Minimal fields for reference semantics; actual packaging data
      is resolved separately through the packaging registry
    - Versionable: Optional version field for pinning specific packaging configs
    - Verifiable: Optional digest for content-addressable resolution

Thread Safety:
    ModelPackagingMetadataRef is immutable after creation (frozen Pydantic model).
    Thread-safe for concurrent read access.

Example:
    >>> # Create a basic packaging reference
    >>> ref = ModelPackagingMetadataRef(ref="pkg:omnibase-core/node-validator")
    >>> ref.ref
    'pkg:omnibase-core/node-validator'

    >>> # Create a versioned reference with digest
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>> ref = ModelPackagingMetadataRef(
    ...     ref="pkg:omnibase-core/node-validator",
    ...     version=ModelSemVer(major=1, minor=0, patch=0),
    ...     digest="sha256:abc123...",
    ...     source="https://registry.omninode.ai/packages"
    ... )

See Also:
    - ModelNodeRef: For referencing nodes within contracts
    - ModelContractReference: For $ref resolution in contracts
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelPackagingMetadataRef(BaseModel):
    """
    Opaque reference to packaging metadata configuration.

    This model serves as a lightweight, stable identifier for packaging metadata
    that is resolved at runtime through a registry or resolver. The actual
    packaging configuration (import paths, dependencies, artifact locations, etc.)
    is retrieved by resolving this reference.

    The reference-based design enables:
        - Decoupling of contract definitions from packaging implementation details
        - Registry-based resolution for flexible deployment strategies
        - Content-addressable packaging with optional digest verification
        - Version pinning for reproducible deployments

    Attributes:
        ref: Opaque stable identifier for the packaging metadata. The format is
            intentionally unspecified to allow registry-specific implementations
            (e.g., URIs, UUIDs, package URLs, or custom slugs).
        digest: Optional content digest/checksum for verifying the resolved
            packaging configuration matches expectations. Format depends on
            the hashing algorithm (e.g., "sha256:abc123...").
        version: Optional semantic version for pinning a specific version of
            the packaging configuration. Useful when packaging metadata evolves
            over time and reproducibility is required.
        source: Optional source location or registry URL where the packaging
            metadata can be resolved. Provides explicit registry targeting when
            multiple registries are available.

    Example:
        >>> ref = ModelPackagingMetadataRef(ref="omnibase-core:node-validator:v1")
        >>> ref.ref
        'omnibase-core:node-validator:v1'
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    ref: str = Field(
        ...,
        description=(
            "Opaque stable identifier for the packaging metadata. "
            "Resolved at runtime via registry to retrieve actual packaging configuration."
        ),
        min_length=1,
    )

    digest: str | None = Field(
        default=None,
        description=(
            "Optional content digest/checksum for verifying the resolved packaging "
            "configuration (e.g., 'sha256:abc123...')."
        ),
    )

    version: ModelSemVer | None = Field(
        default=None,
        description=(
            "Optional semantic version for pinning a specific version of the "
            "packaging configuration."
        ),
    )

    source: str | None = Field(
        default=None,
        description=(
            "Optional source location or registry URL where the packaging metadata "
            "can be resolved."
        ),
    )

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        parts = [f"ref={self.ref!r}"]
        if self.version:
            parts.append(f"version={self.version}")
        return f"ModelPackagingMetadataRef({', '.join(parts)})"


__all__ = ["ModelPackagingMetadataRef"]

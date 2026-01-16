"""
Node Identity Model for Execution Manifest.

Defines the ModelNodeIdentity model which captures the identity of the node
that was executing during a pipeline run. This is used by the Execution
Manifest to answer "what node was executing?".

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeIdentity(BaseModel):
    """
    Identity of the executing node in a pipeline run.

    This model captures the essential information about which node was
    executing, providing correlation across runs and enabling traceability
    in the execution manifest.

    The identity must be stable enough to correlate runs across time,
    meaning the same node executing the same logic should produce the
    same identity values.

    Attributes:
        node_id: Unique identifier for the node instance
        node_kind: Architectural role (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR)
        node_version: Semantic version of the node implementation
        handler_descriptor_id: Optional handler descriptor ID or hash
        namespace: Optional namespace grouping the node
        display_name: Optional human-readable name for display purposes
        runtime_identity: Optional runtime service or process identity (e.g., pod name, PID)

    Example:
        >>> from omnibase_core.enums.enum_node_kind import EnumNodeKind
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>> identity = ModelNodeIdentity(
        ...     node_id="compute-text-transform-001",
        ...     node_kind=EnumNodeKind.COMPUTE,
        ...     node_version=ModelSemVer(major=1, minor=2, patch=0),
        ...     namespace="onex.text",
        ...     display_name="Text Transformer",
        ... )
        >>> identity.node_id
        'compute-text-transform-001'

    See Also:
        - :class:`~omnibase_core.models.manifest.model_execution_manifest.ModelExecutionManifest`:
          The parent manifest model that uses this identity
        - :class:`~omnibase_core.enums.enum_node_kind.EnumNodeKind`:
          The enum defining node architectural roles

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    # === Required Identity Fields ===

    node_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the node instance",
    )

    node_kind: EnumNodeKind = Field(
        ...,
        description="Architectural role (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR)",
    )

    node_version: ModelSemVer = Field(
        ...,
        description="Semantic version of the node implementation",
    )

    # === Optional Identity Fields ===

    handler_descriptor_id: str | None = Field(  # string-id-ok: user-facing identifier
        default=None,
        description="Handler descriptor ID or hash if applicable",
    )

    namespace: str | None = Field(
        default=None,
        description="Namespace grouping the node (e.g., 'onex.text')",
    )

    display_name: str | None = Field(
        default=None,
        description="Human-readable name for display purposes",
    )

    runtime_identity: str | None = Field(
        default=None,
        description="Runtime service or process identity (e.g., pod name, PID)",
    )

    # === Utility Methods ===

    def get_qualified_id(self) -> str:
        """
        Get the fully qualified node identifier.

        Returns:
            Qualified ID in format 'namespace/node_id' or just 'node_id'
        """
        if self.namespace:
            return f"{self.namespace}/{self.node_id}"
        return self.node_id

    def get_display_name(self) -> str:
        """
        Get the display name, falling back to node_id if not set.

        Returns:
            The display_name if set, otherwise the node_id
        """
        return self.display_name or self.node_id

    def get_version_string(self) -> str:
        """
        Get the version as a string.

        Returns:
            Version string in format 'major.minor.patch'
        """
        return str(self.node_version)

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        version_str = self.get_version_string()
        return f"Node({self.get_qualified_id()}@{version_str}, kind={self.node_kind.value})"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelNodeIdentity(node_id={self.node_id!r}, "
            f"node_kind={self.node_kind!r}, "
            f"node_version={self.node_version!r}, "
            f"namespace={self.namespace!r})"
        )


# Export for use
__all__ = ["ModelNodeIdentity"]

"""Node view model for dashboard UI projection."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ("ModelNodeView",)


class ModelNodeView(BaseModel):
    """UI projection of node data.

    Thin view model containing only fields needed for dashboard rendering.
    References canonical node models by UUID, consistent with the core
    architecture pattern used throughout the codebase (NodeCoreBase,
    ModelCapabilityView, etc.).

    This is NOT a full domain model - it contains only the subset of
    fields required for dashboard display purposes.

    See Also:
        - :class:`~omnibase_core.models.dashboard.model_capability_view.ModelCapabilityView`:
          Sister view model using UUID for capability_id
        - :class:`~omnibase_core.infrastructure.node_core_base.NodeCoreBase`:
          Base infrastructure class defining node_id as UUID
        - :class:`~omnibase_core.models.metadata.node_info.model_node_core.ModelNodeCore`:
          Full node core metadata model
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # === Required Identity Fields ===

    node_id: UUID = Field(
        ...,
        description="Unique node identifier (UUID)",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Node name",
    )

    # === Optional Display Fields ===

    namespace: str | None = Field(
        default=None,
        description="Node namespace (e.g., 'onex.compute')",
    )
    display_name: str | None = Field(
        default=None,
        description="Human-readable display name",
    )
    node_kind: str | None = Field(
        default=None,
        description="Node kind (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR)",
    )
    node_type: str | None = Field(
        default=None,
        description="Node implementation type",
    )
    version: str | None = Field(
        default=None,
        description="Version string (e.g., '1.2.3')",
    )
    description: str | None = Field(
        default=None,
        description="Short description for display",
    )

    # === Status Fields ===

    status: str | None = Field(
        default=None,
        description="Current operational status",
    )
    health_status: str | None = Field(
        default=None,
        description="Health status indicator",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the node is currently active",
    )
    is_healthy: bool = Field(
        default=True,
        description="Whether the node is healthy",
    )

    # === Capability Summary ===

    capabilities: tuple[str, ...] = Field(
        default=(),
        description="List of capability names for display",
    )

    # === Utility Methods ===

    def get_display_name(self) -> str:
        """Get the display name, falling back to name if not set.

        Returns:
            The display_name if set, otherwise the name
        """
        return self.display_name or self.name

    def get_qualified_id(self) -> str:
        """Get the fully qualified node identifier.

        Returns:
            Qualified ID in format 'namespace/node_id' or just 'node_id'
        """
        node_id_str = str(self.node_id)
        if self.namespace:
            return f"{self.namespace}/{node_id_str}"
        return node_id_str

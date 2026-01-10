# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Node view model for dashboard UI projection."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelNodeView"]


class ModelNodeView(BaseModel):
    """UI projection of node data.

    Thin view model containing only fields needed for dashboard rendering.
    References canonical node models by ID. Uses string-based IDs for
    flexibility in UI contexts, consistent with ModelNodeIdentity.

    This is NOT a full domain model - it contains only the subset of
    fields required for dashboard display purposes.

    See Also:
        - :class:`~omnibase_core.models.manifest.model_node_identity.ModelNodeIdentity`:
          Canonical node identity model for execution manifests
        - :class:`~omnibase_core.models.metadata.node_info.model_node_core.ModelNodeCore`:
          Full node core metadata model
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # === Required Identity Fields ===

    node_id: str = Field(  # string-id-ok: UI display identifier
        ...,
        min_length=1,
        description="Unique node identifier",
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
        if self.namespace:
            return f"{self.namespace}/{self.node_id}"
        return self.node_id

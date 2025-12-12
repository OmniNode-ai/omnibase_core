"""
Authorization Summary Model.

Authorization requirements summary with roles and security clearance information.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.security.model_security_summaries import (
    ModelAuthorizationInfoSummary,
)


class ModelAuthorizationSummary(BaseModel):
    """Authorization requirements summary."""

    authorized_roles: list[str] = Field(
        default=..., description="Roles authorized to process"
    )
    authorized_nodes: list[str] = Field(
        default=..., description="Nodes authorized to process"
    )
    security_clearance_required: str | None = Field(
        default=None,
        description="Required security clearance",
    )

    def get_role_count(self) -> int:
        """Get number of authorized roles."""
        return len(self.authorized_roles)

    def get_node_count(self) -> int:
        """Get number of authorized nodes."""
        return len(self.authorized_nodes)

    def has_role(self, role: str) -> bool:
        """Check if a specific role is authorized."""
        return role in self.authorized_roles

    def has_node(self, node: str) -> bool:
        """Check if a specific node is authorized."""
        return node in self.authorized_nodes

    def requires_clearance(self) -> bool:
        """Check if security clearance is required."""
        return self.security_clearance_required is not None

    def get_clearance_level(self) -> str:
        """Get security clearance level."""
        return self.security_clearance_required or "none"

    def get_authorization_summary(self) -> ModelAuthorizationInfoSummary:
        """Get authorization summary."""
        return ModelAuthorizationInfoSummary(
            role_count=self.get_role_count(),
            node_count=self.get_node_count(),
            clearance_required=self.requires_clearance(),
            clearance_level=self.get_clearance_level(),
            authorized_roles=self.authorized_roles,
            authorized_nodes=self.authorized_nodes,
        )

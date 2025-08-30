"""
Dynamic CLI Action Model.

Replaces hardcoded EnumNodeCliAction with extensible model that
enables plugin extensibility and contract-driven action registration.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelCliAction(BaseModel):
    """
    Dynamic CLI action model that reads from contracts.

    Replaces hardcoded EnumNodeCliAction to allow third-party nodes
    to register their own actions dynamically.
    """

    action_name: str = Field(
        ..., description="Action identifier", pattern="^[a-z][a-z0-9_]*$"
    )
    node_name: str = Field(..., description="Node that provides this action")
    description: str = Field(..., description="Human-readable description")
    deprecated: bool = Field(default=False, description="Whether action is deprecated")
    category: Optional[str] = Field(None, description="Action category for grouping")

    @classmethod
    def from_contract_action(
        cls,
        action_name: str,
        node_name: str,
        description: Optional[str] = None,
        **kwargs,
    ) -> "ModelCliAction":
        """Factory method for creating actions from contract data."""
        return cls(
            action_name=action_name,
            node_name=node_name,
            description=description or f"{action_name} action for {node_name}",
            **kwargs,
        )

    def get_qualified_name(self) -> str:
        """Get fully qualified action name."""
        return f"{self.node_name}:{self.action_name}"

    def matches(self, action_name: str) -> bool:
        """Check if this action matches the given action name."""
        return self.action_name == action_name

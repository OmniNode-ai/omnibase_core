"""
Dynamic CLI Action Model.

Replaces hardcoded EnumNodeCliAction with extensible model that
enables plugin extensibility and contract-driven action registration.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_action_category import EnumActionCategory


class ModelCliAction(BaseModel):
    """
    Dynamic CLI action model that reads from contracts.

    Replaces hardcoded EnumNodeCliAction to allow third-party nodes
    to register their own actions dynamically.
    """

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Globally unique action identifier",
    )
    action_name_id: UUID = Field(..., description="UUID for action name")
    action_display_name: str | None = Field(
        None,
        description="Human-readable action name",
    )
    node_id: UUID = Field(..., description="UUID-based node reference")
    node_display_name: str | None = Field(None, description="Human-readable node name")
    description: str = Field(..., description="Human-readable description")
    deprecated: bool = Field(default=False, description="Whether action is deprecated")
    category: EnumActionCategory | None = Field(
        None,
        description="Action category for grouping",
    )

    @classmethod
    def from_contract_action(
        cls,
        action_name: str,
        node_id: UUID,
        node_name: str,
        description: str | None = None,
        **kwargs: Any,
    ) -> ModelCliAction:
        """Factory method for creating actions from contract data."""
        import hashlib

        # Generate UUIDs from names
        action_hash = hashlib.sha256(action_name.encode()).hexdigest()
        action_name_id = UUID(
            f"{action_hash[:8]}-{action_hash[8:12]}-{action_hash[12:16]}-{action_hash[16:20]}-{action_hash[20:32]}",
        )

        return cls(
            action_name_id=action_name_id,
            action_display_name=action_name,
            node_id=node_id,
            node_display_name=node_name,
            description=description or f"{action_name} action for {node_name}",
            **kwargs,
        )

    def get_qualified_name(self) -> str:
        """Get fully qualified action name."""
        return f"{self.node_display_name}:{self.action_display_name}"

    def get_globally_unique_id(self) -> str:
        """Get globally unique identifier combining action_id and node_id."""
        return f"{self.node_id}:{self.action_id}"

    def matches(self, action_name: str) -> bool:
        """Check if this action matches the given action name."""
        return self.action_display_name == action_name

    def matches_node_id(self, node_id: UUID) -> bool:
        """Check if this action belongs to the specified node ID."""
        return self.node_id == node_id

    def matches_action_id(self, action_id: UUID) -> bool:
        """Check if this action has the specified action ID."""
        return self.action_id == action_id

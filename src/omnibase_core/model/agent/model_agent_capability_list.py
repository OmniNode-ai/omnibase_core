"""Model for agent capability list management."""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability


class ModelAgentCapabilityList(BaseModel):
    """
    Strongly-typed collection for managing agent capabilities.

    Replaces List[EnumAgentCapability] to comply with ONEX standards
    requiring specific typed models instead of generic types.
    """

    capabilities: list[EnumAgentCapability] = Field(
        default_factory=list,
        description="List of agent capabilities",
    )

    def add_capability(self, capability: EnumAgentCapability) -> None:
        """Add a capability to the list if not already present."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def remove_capability(self, capability: EnumAgentCapability) -> bool:
        """Remove a capability from the list."""
        if capability in self.capabilities:
            self.capabilities.remove(capability)
            return True
        return False

    def has_capability(self, capability: EnumAgentCapability) -> bool:
        """Check if a capability exists in the list."""
        return capability in self.capabilities

    def has_all_capabilities(self, required: list[EnumAgentCapability]) -> bool:
        """Check if all required capabilities are present."""
        return all(cap in self.capabilities for cap in required)

    def has_any_capability(self, required: list[EnumAgentCapability]) -> bool:
        """Check if any of the required capabilities are present."""
        return any(cap in self.capabilities for cap in required)

    def to_set(self) -> set[EnumAgentCapability]:
        """Convert to a set for efficient lookups."""
        return set(self.capabilities)

    def count(self) -> int:
        """Get the number of capabilities."""
        return len(self.capabilities)

    def clear(self) -> None:
        """Remove all capabilities."""
        self.capabilities.clear()

    def extend(self, other_capabilities: list[EnumAgentCapability]) -> None:
        """Add multiple capabilities at once."""
        for cap in other_capabilities:
            self.add_capability(cap)

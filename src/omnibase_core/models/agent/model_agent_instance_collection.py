"""Model for agent instance collection management."""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_agent_instance import ModelAgentInstance


class ModelAgentInstanceCollection(BaseModel):
    """
    Strongly-typed collection for managing multiple agent instances.

    Replaces Dict[str, ModelAgentInstance] to comply with ONEX standards
    against generic type usage.
    """

    instances: dict[str, ModelAgentInstance] = Field(
        default_factory=dict,
        description="Map of agent ID to agent instance",
    )

    def add_agent(self, agent_id: str, instance: ModelAgentInstance) -> None:
        """Add an agent instance to the collection."""
        self.instances[agent_id] = instance

    def get_agent(self, agent_id: str) -> ModelAgentInstance | None:
        """Get an agent instance by ID."""
        return self.instances.get(agent_id)

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent instance from the collection."""
        if agent_id in self.instances:
            del self.instances[agent_id]
            return True
        return False

    def list_agent_ids(self) -> list[str]:
        """List all agent IDs in the collection."""
        return list(self.instances.keys())

    def list_agents(self) -> list[ModelAgentInstance]:
        """List all agent instances in the collection."""
        return list(self.instances.values())

    def contains_agent(self, agent_id: str) -> bool:
        """Check if an agent ID exists in the collection."""
        return agent_id in self.instances

    def count(self) -> int:
        """Get the number of agents in the collection."""
        return len(self.instances)

    def clear(self) -> None:
        """Remove all agents from the collection."""
        self.instances.clear()

    def items(self):
        """Get iterator over (agent_id, instance) pairs."""
        return self.instances.items()

    def values(self):
        """Get iterator over agent instances."""
        return self.instances.values()

    def keys(self):
        """Get iterator over agent IDs."""
        return self.instances.keys()

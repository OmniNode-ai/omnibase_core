"""Model for mapping devices to agent instances."""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_device_type import EnumDeviceType
from omnibase_core.model.core.model_agent_instance import ModelAgentInstance


class ModelAgentDeviceMap(BaseModel):
    """
    Strongly-typed mapping of devices to agent instances.

    Replaces Dict[EnumDeviceType, List[ModelAgentInstance]] to comply
    with ONEX standards requiring specific typed models.
    """

    device_agents: dict[EnumDeviceType, list[ModelAgentInstance]] = Field(
        default_factory=lambda: {
            EnumDeviceType.MAC_STUDIO: [],
            EnumDeviceType.MACBOOK_AIR: [],
            EnumDeviceType.MAC_MINI: [],
        },
        description="Map of device types to agent instances",
    )

    def add_agent(self, device: EnumDeviceType, agent: ModelAgentInstance) -> None:
        """Add an agent to a specific device."""
        if device not in self.device_agents:
            self.device_agents[device] = []
        self.device_agents[device].append(agent)

    def get_agents(self, device: EnumDeviceType) -> list[ModelAgentInstance]:
        """Get all agents for a specific device."""
        return self.device_agents.get(device, [])

    def remove_agent(self, device: EnumDeviceType, agent_id: str) -> bool:
        """Remove an agent from a device by agent ID."""
        if device in self.device_agents:
            original_count = len(self.device_agents[device])
            self.device_agents[device] = [
                agent
                for agent in self.device_agents[device]
                if agent.agent_id != agent_id
            ]
            return len(self.device_agents[device]) < original_count
        return False

    def find_agent(self, agent_id: str) -> ModelAgentInstance | None:
        """Find an agent across all devices by ID."""
        for agents in self.device_agents.values():
            for agent in agents:
                if agent.agent_id == agent_id:
                    return agent
        return None

    def get_device_for_agent(self, agent_id: str) -> EnumDeviceType | None:
        """Get the device type where an agent is running."""
        for device, agents in self.device_agents.items():
            for agent in agents:
                if agent.agent_id == agent_id:
                    return device
        return None

    def count_agents(self, device: EnumDeviceType | None = None) -> int:
        """Count agents on a specific device or all devices."""
        if device:
            return len(self.device_agents.get(device, []))
        return sum(len(agents) for agents in self.device_agents.values())

    def get_all_agents(self) -> list[ModelAgentInstance]:
        """Get all agents across all devices."""
        all_agents = []
        for agents in self.device_agents.values():
            all_agents.extend(agents)
        return all_agents

    def clear_device(self, device: EnumDeviceType) -> None:
        """Clear all agents from a specific device."""
        if device in self.device_agents:
            self.device_agents[device].clear()

    def clear_all(self) -> None:
        """Clear all agents from all devices."""
        for device in self.device_agents:
            self.device_agents[device].clear()

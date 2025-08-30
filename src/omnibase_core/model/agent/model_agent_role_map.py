"""Model for mapping roles to agent instances."""

from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_agent_instance import ModelAgentInstance


class ModelAgentRoleMap(BaseModel):
    """
    Strongly-typed mapping of roles to agent instances.

    Replaces Dict[str, List[ModelAgentInstance]] to comply with ONEX
    standards requiring specific typed models.
    """

    role_agents: Dict[str, List[ModelAgentInstance]] = Field(
        default_factory=dict, description="Map of role names to agent instances"
    )

    def add_agent(self, role: str, agent: ModelAgentInstance) -> None:
        """Add an agent to a specific role."""
        if role not in self.role_agents:
            self.role_agents[role] = []
        self.role_agents[role].append(agent)

    def get_agents(self, role: str) -> List[ModelAgentInstance]:
        """Get all agents for a specific role."""
        return self.role_agents.get(role, [])

    def remove_agent(self, role: str, agent_id: str) -> bool:
        """Remove an agent from a role by agent ID."""
        if role in self.role_agents:
            original_count = len(self.role_agents[role])
            self.role_agents[role] = [
                agent for agent in self.role_agents[role] if agent.agent_id != agent_id
            ]
            # Remove empty role entries
            if not self.role_agents[role]:
                del self.role_agents[role]
            return len(self.role_agents.get(role, [])) < original_count
        return False

    def find_agent(self, agent_id: str) -> Optional[ModelAgentInstance]:
        """Find an agent across all roles by ID."""
        for agents in self.role_agents.values():
            for agent in agents:
                if agent.agent_id == agent_id:
                    return agent
        return None

    def get_roles_for_agent(self, agent_id: str) -> List[str]:
        """Get all roles assigned to a specific agent."""
        roles = []
        for role, agents in self.role_agents.items():
            for agent in agents:
                if agent.agent_id == agent_id:
                    roles.append(role)
        return roles

    def get_available_roles(self) -> Set[str]:
        """Get all available roles that have agents."""
        return set(self.role_agents.keys())

    def count_agents(self, role: Optional[str] = None) -> int:
        """Count agents for a specific role or all roles."""
        if role:
            return len(self.role_agents.get(role, []))
        return sum(len(agents) for agents in self.role_agents.values())

    def get_all_agents(self) -> List[ModelAgentInstance]:
        """Get all unique agents across all roles."""
        # Use dict to maintain uniqueness by agent_id
        unique_agents = {}
        for agents in self.role_agents.values():
            for agent in agents:
                unique_agents[agent.agent_id] = agent
        return list(unique_agents.values())

    def clear_role(self, role: str) -> None:
        """Clear all agents from a specific role."""
        if role in self.role_agents:
            del self.role_agents[role]

    def clear_all(self) -> None:
        """Clear all agents from all roles."""
        self.role_agents.clear()

    def update_agent_role(self, agent_id: str, old_role: str, new_role: str) -> bool:
        """Move an agent from one role to another."""
        # Find the agent in old role
        agent = None
        if old_role in self.role_agents:
            for a in self.role_agents[old_role]:
                if a.agent_id == agent_id:
                    agent = a
                    break

        if agent:
            # Remove from old role
            self.remove_agent(old_role, agent_id)
            # Add to new role
            self.add_agent(new_role, agent)
            return True
        return False

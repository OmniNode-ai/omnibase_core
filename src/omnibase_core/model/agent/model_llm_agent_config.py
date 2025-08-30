"""
Model for LLM agent configuration supporting multiple providers.

Extends the basic agent config to support Ollama, Claude, and other LLM providers
with proper ONEX strong typing and dynamic configuration.
"""

from typing import List, Optional
from uuid import uuid4

from pydantic import Field

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.model.agent.model_llm_provider_config import \
    ModelLLMProviderConfig
from omnibase_core.model.configuration.model_agent_config import \
    ModelAgentConfig


class ModelLLMAgentConfig(ModelAgentConfig):
    """
    Extended agent configuration for multi-provider LLM support.

    Supports Claude, Ollama, and other LLM providers with unified configuration.
    Agent IDs are dynamically generated with provider_model_uuid pattern.
    """

    # Provider configuration
    llm_provider_config: ModelLLMProviderConfig = Field(
        ..., description="LLM provider-specific configuration"
    )

    # Agent capabilities based on model
    capabilities: List[EnumAgentCapability] = Field(
        default_factory=list, description="Agent capabilities for task routing"
    )

    # Fallback providers for resilience
    fallback_providers: List[ModelLLMProviderConfig] = Field(
        default_factory=list,
        description="Fallback provider configurations if primary fails",
    )

    # Task routing preferences
    preferred_task_types: List[str] = Field(
        default_factory=list, description="Types of tasks this agent prefers to handle"
    )

    # Resource constraints
    max_concurrent_tasks: int = Field(1, description="Maximum concurrent tasks")
    memory_limit_mb: Optional[int] = Field(None, description="Memory limit in MB")

    # Agent role/purpose for descriptive naming
    agent_role: str = Field(
        ...,
        description="Descriptive role of the agent (e.g., 'code_reviewer', 'documentation_writer')",
    )

    def generate_agent_id(self) -> str:
        """Generate a dynamic agent ID based on role and UUID."""
        # Normalize the role to be URL-safe
        normalized_role = self.agent_role.lower().replace(" ", "_").replace("-", "_")
        unique_id = str(uuid4())[:8]
        return f"{normalized_role}_{unique_id}"

    def model_post_init(self, __context) -> None:
        """Auto-generate agent_id if not provided."""
        super().model_post_init(__context)
        if not self.agent_id:
            self.agent_id = self.generate_agent_id()

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "name": "Documentation Writer Agent",
                "description": "Specialized agent for writing technical documentation",
                "agent_role": "documentation_writer",
                "llm_provider_config": {
                    "provider": "ollama",
                    "model_id": "mistral:7b-instruct",
                    "endpoint": {
                        "host": "${MAC_STUDIO_HOST}",
                        "port": 11434,
                        "protocol": "http",
                    },
                    "context_length": 8192,
                    "temperature": 0.7,
                },
                "capabilities": ["documentation", "technical_writing", "explanation"],
                "preferred_task_types": [
                    "write_documentation",
                    "create_readme",
                    "explain_code",
                ],
                "working_directory": "${AGENT_WORK_DIR}/documentation",
                "permissions": {
                    "read_files": True,
                    "write_files": True,
                    "execute_commands": False,
                },
            }
        }

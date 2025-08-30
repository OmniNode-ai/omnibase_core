"""
Model for Claude Code agent instance.

This model represents a running Claude Code agent instance with its
configuration, status, and runtime information.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.agent.model_llm_agent_config import ModelLLMAgentConfig
from omnibase_core.model.core.model_agent_status import (
    AgentStatusType,
    ModelAgentStatus,
)


class ModelAgentInstance(BaseModel):
    """Complete agent instance representation."""

    agent_id: str = Field(description="Unique identifier for the agent instance")
    config: ModelLLMAgentConfig = Field(description="Unified LLM agent configuration")
    status: ModelAgentStatus = Field(description="Current agent status")
    process_id: int | None = Field(
        default=None,
        description="Operating system process ID",
    )
    endpoint_url: str | None = Field(
        default=None,
        description="HTTP endpoint URL for agent communication",
    )
    websocket_url: str | None = Field(
        default=None,
        description="WebSocket URL for real-time communication",
    )
    api_client_id: str | None = Field(
        default=None,
        description="Anthropic API client identifier",
    )
    session_token: str | None = Field(
        default=None,
        description="Session token for agent authentication",
    )
    working_directory: str = Field(description="Current working directory")
    log_file_path: str | None = Field(
        default=None,
        description="Path to agent log file",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Instance creation timestamp",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Agent start timestamp",
    )
    terminated_at: datetime | None = Field(
        default=None,
        description="Agent termination timestamp",
    )
    last_heartbeat: datetime | None = Field(
        default=None,
        description="Last heartbeat timestamp",
    )

    @property
    def is_active(self) -> bool:
        """Check if agent is currently active."""
        return self.status.status in [
            AgentStatusType.IDLE,
            AgentStatusType.WORKING,
            AgentStatusType.STARTING,
        ]

    @property
    def is_available(self) -> bool:
        """Check if agent is available for new work."""
        return self.status.status == AgentStatusType.IDLE

    @property
    def uptime_seconds(self) -> int:
        """Calculate agent uptime in seconds."""
        if self.started_at is None:
            return 0

        end_time = self.terminated_at or datetime.now()
        return int((end_time - self.started_at).total_seconds())

    @classmethod
    def generate_agent_id(cls, task_type: str) -> str:
        """
        Generate human-readable agent ID with format: task_type_uuid_suffix

        Examples:
            - fix_any_types_9d4e5f6a
            - enhance_error_handling_a7f3b2c1
            - modernize_registry_pattern_2b3c4d5e

        Args:
            task_type: Brief task description in snake_case format

        Returns:
            Agent ID string with UUID suffix
        """
        # Validate task type format
        if not task_type.replace("_", "").isalnum():
            msg = "Task type must be alphanumeric with underscores only"
            raise ValueError(msg)
        if task_type != task_type.lower():
            msg = "Task type must be lowercase"
            raise ValueError(msg)

        # Generate 8-character UUID suffix
        uuid_suffix = str(uuid.uuid4()).replace("-", "")[:8]
        return f"{task_type}_{uuid_suffix}"

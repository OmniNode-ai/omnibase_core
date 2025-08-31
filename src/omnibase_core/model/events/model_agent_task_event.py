"""
Event models for distributed agent task communication.

Defines strongly-typed events for agent orchestration that work seamlessly
across both in-memory ONEX event bus and Kafka (Confluent Cloud).
These events follow ONEX event patterns and can be wrapped in ModelEventEnvelope
for routing through the distributed system.

Event Types:
- agent.task.request: Request to execute a task
- agent.task.assignment: Task assignment to an agent
- agent.task.progress: Progress update for a task
- agent.task.result: Task completion result
- agent.status.update: Agent status heartbeat
- agent.discovery.request: Request to discover agents
- agent.discovery.response: Response with discovered agents
"""

from omnibase_core.model.events.model_agent_discovery_request import (
    ModelAgentDiscoveryRequest,
)
from omnibase_core.model.events.model_agent_discovery_response import (
    ModelAgentDiscoveryResponse,
)
from omnibase_core.model.events.model_agent_status_update import ModelAgentStatusUpdate
from omnibase_core.model.events.model_agent_task_assignment import (
    ModelAgentTaskAssignment,
)
from omnibase_core.model.events.model_agent_task_progress import ModelAgentTaskProgress

# Re-export all event models for backward compatibility
from omnibase_core.model.events.model_agent_task_request import ModelAgentTaskRequest
from omnibase_core.model.events.model_agent_task_result import ModelAgentTaskResult

__all__ = [
    "ModelAgentDiscoveryRequest",
    "ModelAgentDiscoveryResponse",
    "ModelAgentStatusUpdate",
    "ModelAgentTaskAssignment",
    "ModelAgentTaskProgress",
    "ModelAgentTaskRequest",
    "ModelAgentTaskResult",
]

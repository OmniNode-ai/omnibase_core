"""
Workflow Dependency Type Enumeration.

Defines the types of dependencies that can exist between workflows
in the orchestrator pattern for proper type safety and validation.
"""

from enum import Enum, unique


@unique
class EnumWorkflowDependencyType(Enum):
    """Types of workflow dependencies for orchestration patterns."""

    SEQUENTIAL = "sequential"
    """Sequential dependency where one workflow must complete before another starts."""

    PARALLEL = "parallel"
    """Parallel dependency where workflows can run concurrently."""

    CONDITIONAL = "conditional"
    """Conditional dependency based on workflow outcome or state."""

    BLOCKING = "blocking"
    """Blocking dependency that prevents workflow execution until cleared."""

    COMPENSATING = "compensating"
    """Compensating dependency for saga pattern rollback scenarios."""

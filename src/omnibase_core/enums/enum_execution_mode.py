from __future__ import annotations

"""
Execution Mode Enum.

Strongly typed execution mode values for configuration - defines WHICH pattern to use for processing.
"""


from enum import Enum, unique


@unique
class EnumExecutionMode(str, Enum):
    """
    Execution pattern mode - WHICH pattern to use for processing.

    Defines the execution pattern/approach for processing:
    - DIRECT: Direct synchronous execution
    - WORKFLOW: LlamaIndex workflow-based execution
    - ORCHESTRATED: Hub-orchestrated execution via Generation Hub
    - AUTO: Automatic mode selection based on complexity
    """

    DIRECT = "direct"
    WORKFLOW = "workflow"
    ORCHESTRATED = "orchestrated"
    AUTO = "auto"


# Export for use
__all__ = ["EnumExecutionMode"]

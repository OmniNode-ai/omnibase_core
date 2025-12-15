"""Workflow context type alias for flexible runtime state.

This type alias is used by ModelWorkflowStateSnapshot to represent workflow context data.
Workflow contexts inherently need flexibility because they can contain arbitrary runtime
state that varies per workflow implementation (e.g., step results, error info, metadata).

Design Decision:
    Using dict[str, Any] is intentional here because:
    1. Workflow contexts are inherently flexible and vary per implementation
    2. The context can contain any runtime state needed by specific workflows
    3. Type safety for context values is enforced at the workflow executor level
    4. This aligns with common workflow patterns in other frameworks

Note:
    This file is in /types/ directory which is excluded from dict[str, Any] validation.
    This is the recommended pattern for intentional flexible typing.
"""

from typing import Any

# Type alias for workflow context - flexible runtime state storage
# Intentionally uses dict[str, Any] for workflow flexibility
WorkflowContextType = dict[str, Any]

__all__ = ["WorkflowContextType"]

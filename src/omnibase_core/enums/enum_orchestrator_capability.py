"""
Orchestrator Capability Enumeration.

Defines the available capabilities for ORCHESTRATOR nodes in the ONEX four-node architecture.
ORCHESTRATOR nodes handle workflow coordination including multi-step workflows,
parallel execution, and error recovery.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn


@unique
class EnumOrchestratorCapability(str, Enum):
    """
    Enumeration of supported orchestrator node capabilities.

    SINGLE SOURCE OF TRUTH for orchestrator capability values.
    Replaces magic strings in handler capability constants.

    Using an enum instead of raw strings:
    - Prevents typos ("workflow_resolver" vs "workflowResolver")
    - Enables IDE autocompletion
    - Provides exhaustiveness checking
    - Centralizes capability definitions
    - Preserves full type safety

    Capabilities:
        WORKFLOW_RESOLVER: Workflow resolution and coordination capability

    Example:
        >>> from omnibase_core.enums import EnumOrchestratorCapability
        >>> cap = EnumOrchestratorCapability.WORKFLOW_RESOLVER
        >>> str(cap)
        'workflow_resolver'
        >>> cap.value
        'workflow_resolver'
    """

    WORKFLOW_RESOLVER = "workflow_resolver"
    """Workflow resolution and coordination capability."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def values(cls) -> list[str]:
        """Return all capability values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling of all enum values in match statements.

        This method enables static type checkers to verify that all enum values
        are handled in match/case statements. If a case is missing, mypy will
        report an error at the call site.

        Usage:
            match capability:
                case EnumOrchestratorCapability.WORKFLOW_RESOLVER:
                    handle_workflow()
                case _ as unreachable:
                    EnumOrchestratorCapability.assert_exhaustive(unreachable)

        Args:
            value: The unhandled enum value (typed as Never for exhaustiveness).

        Raises:
            AssertionError: Always raised if this code path is reached at runtime.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumOrchestratorCapability"]

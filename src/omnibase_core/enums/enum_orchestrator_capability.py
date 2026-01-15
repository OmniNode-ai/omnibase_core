"""
Orchestrator Capability Enumeration.

Defines the available capabilities for ORCHESTRATOR nodes in the ONEX four-node architecture.
ORCHESTRATOR nodes handle workflow coordination including multi-step workflows,
parallel execution, and error recovery.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOrchestratorCapability(StrValueHelper, str, Enum):
    """Orchestrator node capabilities (currently: WORKFLOW_RESOLVER for coordination)."""

    WORKFLOW_RESOLVER = "workflow_resolver"
    """Workflow resolution and coordination capability."""

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

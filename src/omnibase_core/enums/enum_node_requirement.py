"""
Node Requirement Enumeration.

Defines the required handler capabilities for each node type in the ONEX four-node
architecture. These are the minimum capabilities that handlers MUST implement
for a given node type.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeRequirement(StrValueHelper, str, Enum):
    """
    Enumeration of node handler requirements.

    SINGLE SOURCE OF TRUTH for node requirement values.
    Replaces magic strings in NODE_TYPE_REQUIREMENTS mapping.

    These represent the minimum capabilities that handlers MUST implement
    for a given node type:
    - EFFECT nodes require HANDLER_EXECUTE (execute method)
    - REDUCER nodes require FSM_INTERPRETER (state machine support)
    - ORCHESTRATOR nodes require WORKFLOW_RESOLVER (workflow coordination)
    - COMPUTE nodes have no required capabilities

    Using an enum instead of raw strings:
    - Prevents typos ("handler_execute" vs "handlerExecute")
    - Enables IDE autocompletion
    - Provides exhaustiveness checking
    - Centralizes requirement definitions
    - Preserves full type safety

    Requirements:
        HANDLER_EXECUTE: Required handler execute() method
        FSM_INTERPRETER: Required FSM interpreter capability
        WORKFLOW_RESOLVER: Required workflow resolver capability

    Example:
        >>> from omnibase_core.enums import EnumNodeRequirement
        >>> req = EnumNodeRequirement.HANDLER_EXECUTE
        >>> str(req)
        'handler_execute'
        >>> req.value
        'handler_execute'
    """

    HANDLER_EXECUTE = "handler_execute"
    """Required handler execute() method for EFFECT nodes."""

    FSM_INTERPRETER = "fsm_interpreter"
    """Required FSM interpreter capability for REDUCER nodes."""

    WORKFLOW_RESOLVER = "workflow_resolver"
    """Required workflow resolver capability for ORCHESTRATOR nodes."""

    @classmethod
    def values(cls) -> list[str]:
        """Return all requirement values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling of all enum values in match statements.

        This method enables static type checkers to verify that all enum values
        are handled in match/case statements. If a case is missing, mypy will
        report an error at the call site.

        Usage:
            match requirement:
                case EnumNodeRequirement.HANDLER_EXECUTE:
                    handle_execute()
                case EnumNodeRequirement.FSM_INTERPRETER:
                    handle_fsm()
                case EnumNodeRequirement.WORKFLOW_RESOLVER:
                    handle_workflow()
                case _ as unreachable:
                    EnumNodeRequirement.assert_exhaustive(unreachable)

        Args:
            value: The unhandled enum value (typed as Never for exhaustiveness).

        Raises:
            AssertionError: Always raised if this code path is reached at runtime.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumNodeRequirement"]

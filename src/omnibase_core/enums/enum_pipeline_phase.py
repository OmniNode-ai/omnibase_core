# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Pipeline Phase Enumeration for ticket-pipeline execution lifecycle.

Phases in the ticket-pipeline execution lifecycle. Each ticket processed by
``ticket-pipeline`` moves through a sequence of phases from ``INTAKE`` to
``DONE`` (or ``FAILED`` for unrecoverable failures).

**Transition policy:** This enum defines valid phase names, NOT valid
transitions between them. Pipeline phase transition rules (which skill results
trigger advancement, which trigger retry, which trigger FAILED) are defined in
``ticket-pipeline/SKILL.md``, not in this enum. Consumers must not infer
transition semantics from enum ordering alone.

Terminal phases
---------------

- ``DONE`` -- Successful completion of all pipeline phases.
- ``FAILED`` -- Unrecoverable pipeline failure. Distinct from a phase that
  produces a ``failed`` skill result (which may trigger retry). ``FAILED``
  means the pipeline itself has given up.

.. versionadded:: 0.7.0
    Added as part of OMN-3870 to formalize the ticket-pipeline phase
    vocabulary for ``ModelPipelineState``.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumPipelinePhase", "PipelinePhaseEnum"]


@unique
class EnumPipelinePhase(StrValueHelper, str, Enum):
    """Phases in the ticket-pipeline execution lifecycle.

    **Transition policy:** This enum defines valid phase names, NOT valid
    transitions between them. Pipeline phase transition rules (which skill
    results trigger advancement, which trigger retry, which trigger FAILED)
    are defined in ``ticket-pipeline/SKILL.md``, not in this enum. Consumers
    must not infer transition semantics from enum ordering alone.
    """

    INTAKE = "intake"
    """Initial ticket analysis and validation."""

    RESEARCH = "research"
    """Background research and context gathering."""

    SPEC = "spec"
    """Specification and design phase."""

    IMPLEMENT = "implement"
    """Code implementation phase."""

    LOCAL_REVIEW = "local_review"
    """Local adversarial review before CI."""

    CI_WATCH = "ci_watch"
    """Watching CI pipeline for pass/fail."""

    PR_WATCH = "pr_watch"
    """Watching PR for review feedback."""

    CONTRACT_COMPLIANCE = "contract_compliance"
    """Verifying contract compliance."""

    AUTO_MERGE = "auto_merge"
    """Automated merge attempt."""

    DONE = "done"
    """Successful completion of all pipeline phases. Terminal."""

    FAILED = "failed"
    """Unrecoverable pipeline failure. Terminal.

    Distinct from a phase producing a ``failed`` skill result (which may
    trigger retry). ``FAILED`` means the pipeline itself has given up.
    """

    @property
    def is_terminal(self) -> bool:
        """Whether this phase represents a final pipeline state.

        Terminal phases (``DONE``, ``FAILED``) indicate the pipeline has
        finished execution and will not advance further.

        Returns:
            True if the phase is a final state.
        """
        return self in _TERMINAL_PHASES


# Constant set defined after the class for self-referential enum values.
_TERMINAL_PHASES: frozenset[EnumPipelinePhase] = frozenset(
    {
        EnumPipelinePhase.DONE,
        EnumPipelinePhase.FAILED,
    }
)


# Alias for convenience (matches existing enum aliasing patterns in omnibase_core)
PipelinePhaseEnum = EnumPipelinePhase

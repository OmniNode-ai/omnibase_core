# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Skill Result Status Enumeration for skill execution outcomes.

Canonical status categories for skill execution results. Skills write result
files to ~/.claude/skill-results/. This enum normalizes the 28+ ad-hoc status
strings observed across 40+ skills into 9 semantic categories. Skills needing
domain-specific granularity should use the ``extra_status`` field on
ModelSkillResult rather than extending this enum.

Behavioral definitions
----------------------

Each value has an explicit behavioral classification:

- ``success`` -- Expected successful completion, all goals met. Terminal, success-like.
- ``partial`` -- Mixed or degraded but usable outcome. Terminal, success-like.
- ``failed`` -- Domain-level negative outcome (CI red, review rejected). Terminal.
- ``error`` -- Infrastructure/tool failure (network timeout, parse failure). Terminal.
- ``blocked`` -- Waiting on external dependency or prerequisite. Non-terminal.
- ``skipped`` -- Intentionally not executed, not needed. Terminal.
- ``dry_run`` -- Simulated only, no side effects produced. Terminal, success-like.
- ``pending`` -- Execution started but not yet resolved. Non-terminal.
- ``gated`` -- Awaiting explicit human approval. Non-terminal.

**Hard rule for failed vs error:**
``failed`` = the skill ran its logic and the outcome was negative.
``error`` = the skill could not run its logic due to infrastructure/tooling
problems. If you can answer "what was the domain result?", it's ``failed``.
If the answer is "there was no domain result because something broke", it's
``error``.

**Transition policy:** This enum defines valid phase names, NOT valid
transitions between them. Consumers must not infer transition semantics from
enum ordering alone.

.. versionadded:: 0.7.0
    Added as part of OMN-3866 to replace ad-hoc status strings with a
    canonical enum for skill result files.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumSkillResultStatus", "SkillResultStatus"]


@unique
class EnumSkillResultStatus(StrValueHelper, str, Enum):
    """Canonical status categories for skill execution results.

    Skills write result files to ``~/.claude/skill-results/``. This enum
    normalizes the 28+ ad-hoc status strings into 9 semantic categories.
    Skills needing domain-specific granularity should use the
    ``extra_status`` field on ``ModelSkillResult``.

    **Transition policy:** This enum defines valid phase names, NOT valid
    transitions between them. Consumers must not infer transition semantics
    from enum ordering alone.
    """

    SUCCESS = "success"
    """Expected successful completion -- all goals met. Terminal, success-like."""

    PARTIAL = "partial"
    """Mixed or degraded but usable outcome -- some goals met, some failed.
    Terminal, success-like."""

    FAILED = "failed"
    """Expected domain-level negative outcome -- the task was attempted and
    produced a known-bad result (CI red, review rejected, merge conflict).
    Terminal, not success-like.

    Use ``failed`` when the skill ran its logic and the outcome was negative.
    """

    ERROR = "error"
    """Unexpected runtime/infrastructure/tool failure -- not a domain outcome,
    an execution problem (network timeout, API error, parse failure).
    Terminal, not success-like.

    Use ``error`` when the skill could not run its logic due to
    infrastructure/tooling problems.
    """

    BLOCKED = "blocked"
    """Waiting on external dependency or missing prerequisite -- cannot proceed
    until something else happens. Non-terminal, not success-like."""

    SKIPPED = "skipped"
    """Intentionally not executed -- not needed or already satisfied. Terminal,
    not success-like."""

    DRY_RUN = "dry_run"
    """Simulated only, no side effects produced. Terminal, success-like."""

    PENDING = "pending"
    """Execution started but not yet resolved. Non-terminal, not success-like."""

    GATED = "gated"
    """Awaiting explicit human approval before proceeding. Non-terminal, not
    success-like."""

    @property
    def is_terminal(self) -> bool:
        """Whether this status indicates no further processing is expected.

        Terminal statuses represent final outcomes. Non-terminal statuses
        (``PENDING``, ``BLOCKED``, ``GATED``) may transition to a terminal
        status later.

        Returns:
            True if the status is a final outcome, False if further
            processing may occur.
        """
        return self in _TERMINAL_STATUSES

    @property
    def is_success_like(self) -> bool:
        """Whether this status counts as a positive outcome for downstream consumers.

        Success-like statuses indicate the skill achieved its goals (fully or
        partially) or ran in simulation mode. Consumers use this to decide
        whether to advance a pipeline or retry.

        Returns:
            True if the status represents a positive or usable outcome.
        """
        return self in _SUCCESS_LIKE_STATUSES


# Constant sets defined after the class to allow self-referential enum values.
_TERMINAL_STATUSES: frozenset[EnumSkillResultStatus] = frozenset(
    {
        EnumSkillResultStatus.SUCCESS,
        EnumSkillResultStatus.PARTIAL,
        EnumSkillResultStatus.FAILED,
        EnumSkillResultStatus.ERROR,
        EnumSkillResultStatus.SKIPPED,
        EnumSkillResultStatus.DRY_RUN,
    }
)

_SUCCESS_LIKE_STATUSES: frozenset[EnumSkillResultStatus] = frozenset(
    {
        EnumSkillResultStatus.SUCCESS,
        EnumSkillResultStatus.PARTIAL,
        EnumSkillResultStatus.DRY_RUN,
    }
)


# Alias for convenience (matches existing enum aliasing patterns in omnibase_core)
SkillResultStatus = EnumSkillResultStatus

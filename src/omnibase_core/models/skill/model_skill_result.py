# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelSkillResult -- base contract for skill execution result files.

Written to ``~/.claude/skill-results/{context_id}/{skill_name}.json``
by producer skills.  Consumer skills (epic-team, ticket-pipeline) read
these files to determine next actions.

**Frozen:** Results are immutable after creation.  Common fields cover
the 6 most frequently used across 40+ skills.  Skill-specific data goes
in ``extra`` dict, accessed by key.  ``extra_status`` preserves
domain-specific status strings (e.g. ``"merged"``, ``"clean_with_nits"``)
alongside the canonical enum.

**Promotion rule for ``extra`` fields:**

- If a field appears in **3+ producer skills**, open a ticket to evaluate
  promotion to a first-class field.
- If any **orchestrator consumer** (epic-team, ticket-pipeline) branches
  on ``extra["x"]``, that field MUST be promoted.
- ``extra`` is a migration bridge, not a permanent schema extension
  mechanism.

**File lifecycle:** Skills write exactly one final result file per
execution.  Non-terminal statuses (``pending``, ``gated``, ``blocked``)
may appear in intermediate writes that are overwritten.  The last write
is the authoritative result.  Model instances are frozen (immutable in
memory), but the file on disk may be overwritten during execution.

**Write safety:** Producers MUST use atomic write (temp file +
``os.rename()``) to prevent consumers from reading partial files.
Consumers SHOULD retry once on ``json.JSONDecodeError`` (transient
partial-read during atomic rename window).

.. versionadded:: 0.7.0
    Added as part of OMN-3867 to replace ad-hoc JSON dicts with a
    validated Pydantic contract for skill result files.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_skill_result_status import EnumSkillResultStatus

__all__ = ["ModelSkillResult", "SkillResult"]

_TICKET_ID_PATTERN = re.compile(r"^[A-Z]+-[0-9]+$")


class ModelSkillResult(BaseModel):
    """Base contract for skill execution result files.

    Written to ``~/.claude/skill-results/{context_id}/{skill_name}.json``
    by producer skills.  Consumer skills (epic-team, ticket-pipeline) read
    these files to determine next actions.

    Frozen: results are immutable after creation.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # ------------------------------------------------------------------
    # Required fields
    # ------------------------------------------------------------------

    skill_name: str = Field(
        ...,
        min_length=1,
        description="Name of the skill that produced this result.",
    )

    status: EnumSkillResultStatus = Field(
        ...,
        description="Canonical execution outcome.",
    )

    # ------------------------------------------------------------------
    # Optional common fields (appear in 5+ skills)
    # ------------------------------------------------------------------

    extra_status: str | None = Field(
        default=None,
        description=(
            "Domain-specific status string preserved from the skill. "
            "Use for granularity beyond the canonical enum."
        ),
    )

    run_id: str | None = Field(
        default=None,
        description="Correlation ID for the pipeline run.",
    )

    repo: str | None = Field(
        default=None,
        description="Repository name or org/repo slug.",
    )

    pr_number: int | None = Field(
        default=None,
        ge=1,
        description="Pull request number. Must be >= 1 when provided.",
    )

    ticket_id: str | None = Field(
        default=None,
        description=(
            "Linear ticket ID (e.g. ``OMN-1234``, ``DASH-56``). "
            "**Scope:** This pattern (``^[A-Z]+-[0-9]+$``) is intentionally "
            "OmniNode-specific, matching Linear ticket IDs. It is NOT a "
            "universal work-item identifier. If the platform adopts UUID-backed "
            "or multi-system ticket references, this field should be loosened "
            "or a new ``work_item_id`` field added. The current restriction is "
            "a deliberate scope constraint, not an accident."
        ),
    )

    # ------------------------------------------------------------------
    # Skill-specific fields
    # ------------------------------------------------------------------

    extra: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Skill-specific fields accessed by key. "
            "See promotion rule in module docstring."
        ),
    )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of result creation (UTC).",
    )

    # ------------------------------------------------------------------
    # Validators (normalization-before-validation)
    # ------------------------------------------------------------------

    @field_validator("skill_name", mode="before")
    @classmethod
    def _normalize_skill_name(cls, v: Any) -> Any:
        """Strip whitespace; reject if empty after strip."""
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("skill_name must not be empty or whitespace-only")
            return stripped
        return v

    @field_validator("ticket_id", mode="before")
    @classmethod
    def _normalize_and_validate_ticket_id(cls, v: Any) -> Any:
        """Strip whitespace; validate against ``^[A-Z]+-[0-9]+$``."""
        if v is None:
            return v
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return None
            if not _TICKET_ID_PATTERN.match(stripped):
                raise ValueError(
                    f"ticket_id must match ^[A-Z]+-[0-9]+$ "
                    f"(e.g. OMN-1234, DASH-56), got {stripped!r}"
                )
            return stripped
        return v

    # ------------------------------------------------------------------
    # Delegated properties
    # ------------------------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        """Delegates to ``EnumSkillResultStatus.is_terminal``."""
        return self.status.is_terminal

    @property
    def is_success_like(self) -> bool:
        """Delegates to ``EnumSkillResultStatus.is_success_like``."""
        return self.status.is_success_like

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string for file I/O."""
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, data: str) -> ModelSkillResult:
        """Deserialize from JSON string."""
        return cls.model_validate_json(data)


# Alias for convenience (matches existing aliasing patterns in omnibase_core)
SkillResult = ModelSkillResult

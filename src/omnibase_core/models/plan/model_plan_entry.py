# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelPlanEntry", "PlanEntry"]

_PLAN_ID_PATTERN = re.compile(r"^P[1-9][0-9]*(?:_[1-9][0-9]*)?$")
_EXTERNAL_DEP_PATTERN = re.compile(r"^OMN-[0-9]+$")


class ModelPlanEntry(BaseModel):
    """A single task/phase/milestone parsed from a plan markdown file.

    Produced by plan-to-tickets' detect_structure() function.
    Consumed by plan-to-tickets (ticket creation) and executing-plans
    (phase-by-phase execution).

    Frozen: plan entries are immutable after parsing.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    id: str = Field(
        ...,
        min_length=1,
        description=(
            "Internal ID normalized to P{N} format (e.g., P1, P2_5). "
            "**Restriction policy:** This regex is intentionally restrictive, "
            "matching only the current plan-to-tickets normalization output "
            "(P1, P12, P3_1). It rejects P1A, P01, P1a, P1_1_2. If "
            "plan-to-tickets evolves its ID scheme, this regex must be "
            "updated in lockstep. The restriction is a contract choice, "
            "not an ontological claim."
        ),
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Entry title (e.g., 'Task 1: Create skill specification').",
    )
    content: str = Field(
        ...,
        description="Full markdown content of this entry (everything between headings).",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description=(
            "Dependency IDs: P{N} for internal, OMN-{N} for external. "
            "**Scope:** External dependency IDs currently match only Linear "
            "ticket format. This is intentionally narrow. Cross-system "
            "references (GitHub issues, Jira tickets) are out of scope "
            "for this contract version."
        ),
    )

    @field_validator("id", mode="before")
    @classmethod
    def _normalize_and_validate_id(cls, v: str) -> str:
        """Strip whitespace, uppercase p -> P, then validate pattern."""
        if not isinstance(v, str):
            # error-ok: Pydantic field_validator requires ValueError/TypeError
            raise TypeError(f"id must be a string, got {type(v).__name__}")
        normalized = v.strip()
        # Uppercase leading 'p' to 'P'
        if normalized.startswith("p"):
            normalized = "P" + normalized[1:]
        if not _PLAN_ID_PATTERN.match(normalized):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Plan entry id {normalized!r} does not match pattern "
                f"^P[1-9][0-9]*(?:_[1-9][0-9]*)?$ (e.g., P1, P12, P3_1)"
            )
        return normalized

    @field_validator("content", mode="before")
    @classmethod
    def _reject_empty_content(cls, v: str) -> str:
        """Reject empty or whitespace-only content."""
        if not isinstance(v, str):
            # error-ok: Pydantic field_validator requires ValueError/TypeError
            raise TypeError(f"content must be a string, got {type(v).__name__}")
        if not v.strip():
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError("Plan entry content must not be empty or whitespace-only.")
        return v

    @field_validator("dependencies", mode="before")
    @classmethod
    def _normalize_and_validate_dependencies(cls, v: list[str]) -> list[str]:
        """Strip whitespace, normalize case, validate each dependency."""
        if not isinstance(v, list):
            # error-ok: Pydantic field_validator requires ValueError/TypeError
            raise TypeError(f"dependencies must be a list, got {type(v).__name__}")
        result: list[str] = []
        for dep in v:
            if not isinstance(dep, str):
                # error-ok: Pydantic field_validator requires ValueError/TypeError
                raise TypeError(
                    f"Each dependency must be a string, got {type(dep).__name__}"
                )
            normalized = dep.strip()
            # Normalize leading lowercase p -> P
            if normalized.startswith("p"):
                normalized = "P" + normalized[1:]
            # Normalize any mixed-case "omn-" prefix to "OMN-" (case-insensitive)
            if normalized.upper().startswith("OMN-"):
                normalized = "OMN-" + normalized[4:]
            if not (
                _PLAN_ID_PATTERN.match(normalized)
                or _EXTERNAL_DEP_PATTERN.match(normalized)
            ):
                # error-ok: Pydantic field_validator requires ValueError
                raise ValueError(
                    f"Dependency {normalized!r} does not match internal pattern "
                    f"^P[1-9][0-9]*(?:_[1-9][0-9]*)?$ or external pattern ^OMN-[0-9]+$"
                )
            result.append(normalized)
        return result


PlanEntry = ModelPlanEntry

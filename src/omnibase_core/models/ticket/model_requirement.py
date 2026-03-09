# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Requirement model for ticket specification."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelRequirement(BaseModel):
    """A requirement for the ticket specification.

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.

    Backward compatibility:
        The ``acceptance`` field previously accepted ``list[str]``. The pre-validator
        ``coerce_legacy_acceptance`` transparently coerces old string entries to
        ``{"id": "ac_N", "statement": <string>}`` dicts so that contracts written
        before ModelAcceptanceCriterion was introduced continue to deserialise
        correctly. This coercion is idempotent for already-structured data.
    """

    id: str = Field(..., description="Unique identifier for the requirement")
    statement: str = Field(..., description="The requirement statement")
    rationale: str | None = Field(
        default=None, description="Reasoning behind the requirement"
    )
    acceptance: list[str] = Field(
        default_factory=list, description="Acceptance criteria for the requirement"
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_acceptance(cls, data: object) -> object:
        """Coerce legacy ``acceptance: list[str]`` to structured dicts.

        Contracts written before ModelAcceptanceCriterion used plain strings.
        This validator converts them to ``{"id": "ac_N", "statement": <str>}``
        so old YAMLs continue to load without changes. Has no effect when the
        list is already structured (list of dicts) or empty.
        """
        if not isinstance(data, dict):
            return data
        acceptance = data.get("acceptance", [])
        if acceptance and isinstance(acceptance[0], str):
            data = dict(data)
            data["acceptance"] = [
                {"id": f"ac_{i + 1}", "statement": item}
                for i, item in enumerate(acceptance)
            ]
        return data


# Alias for cleaner imports
Requirement = ModelRequirement

__all__ = [
    "ModelRequirement",
    "Requirement",
]

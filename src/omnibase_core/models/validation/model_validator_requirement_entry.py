# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed spec entry for validator-requirements.yaml.

Each key under ``required_validators`` in the spec maps to a
``ModelValidatorRequirementEntry``. The enforcement consumer (OMN-9115)
reads the spec, constructs one of these per validator, and uses the typed
fields rather than raw ``dict[str, Any]`` access so that any schema drift
surfaces as a Pydantic validation error rather than a ``KeyError``.

The model mirrors the full spec shape (``extra="forbid"``) so unknown
fields fail loud, and ``pre_commit``/``ci_workflow`` use
``EnumValidatorRequirementScope`` so scope typos (e.g. ``requird``) cannot
silently bypass enforcement.

Related ticket: OMN-9115 (consumer), OMN-9051 (spec), parent OMN-9048.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_validator_requirement_scope import (
    EnumValidatorRequirementScope,
)
from omnibase_core.models.validation.model_validator_requirement_excludes import (
    ModelValidatorRequirementExcludes,
)

__all__ = ["ModelValidatorRequirementEntry"]


class ModelValidatorRequirementEntry(BaseModel):
    """Typed view over a single ``required_validators[*]`` entry."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    description: str = Field(
        description="Human-readable summary of what the validator enforces."
    )
    central_source: str = Field(
        description=(
            "Canonical source module / CLI that hosts the validator "
            "implementation (e.g. 'omnibase_core.validation.validator_x')."
        )
    )
    pre_commit: EnumValidatorRequirementScope = Field(
        description=(
            "pre-commit scope: REQUIRED means repos must wire the hook; "
            "OPTIONAL means repos may skip without producing a gap."
        )
    )
    ci_workflow: EnumValidatorRequirementScope = Field(
        description=(
            "CI workflow scope: REQUIRED means a step must exist; "
            "OPTIONAL means CI coverage is a nice-to-have."
        )
    )
    required_check_on_main: str | None = Field(
        description=(
            "GitHub required-check context name protecting main (e.g. "
            "'SPDX Headers / validate'), or null if not yet wired."
        )
    )
    silent_skip_allowed: bool = Field(
        description=(
            "Must be False; feedback_no_informational_gates forbids advisory "
            "modes. Kept as a field so the spec test can enforce the invariant."
        )
    )
    pre_commit_hook_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Substrings accepted as pre-commit hook ids for this validator. "
            "At least one must match an entry in .pre-commit-config.yaml."
        ),
    )
    ci_workflow_keywords: list[str] = Field(
        default_factory=list,
        description=(
            "Substrings accepted anywhere in .github/workflows/*.yml as "
            "evidence that this validator runs in CI."
        ),
    )
    excludes: ModelValidatorRequirementExcludes = Field(
        description=(
            "Allow/forbid path-regex buckets constraining where the "
            "validator is permitted to skip."
        )
    )
    applies_to_repos: list[str] | str = Field(
        description=(
            "Either the literal string 'all' (every repo) or a list of repo "
            "names. Unknown names are a spec typo, caught by the shape tests."
        )
    )

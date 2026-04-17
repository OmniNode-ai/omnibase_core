# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed spec entry for validator-requirements.yaml.

Each key under ``required_validators`` in the spec maps to a
``ModelValidatorRequirementEntry``. The enforcement consumer (OMN-9115)
reads the spec, constructs one of these per validator, and uses the typed
fields rather than raw ``dict[str, Any]`` access so that any schema drift
surfaces as a Pydantic validation error rather than a ``KeyError``.

Related ticket: OMN-9115 (consumer), OMN-9051 (spec), parent OMN-9048.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelValidatorRequirementEntry"]


class ModelValidatorRequirementEntry(BaseModel):
    """Typed view over a single ``required_validators[*]`` entry."""

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    pre_commit: str = Field(
        description=(
            "pre-commit scope: 'required' means repos must wire the hook; "
            "'optional' means repos may skip without producing a gap."
        )
    )
    ci_workflow: str = Field(
        description=(
            "CI workflow scope: 'required' means a step must exist; "
            "'optional' means CI coverage is a nice-to-have."
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
    applies_to_repos: list[str] | str = Field(
        description=(
            "Either the literal string 'all' (every repo) or a list of repo "
            "names. Unknown names are a spec typo, caught by the shape tests."
        )
    )

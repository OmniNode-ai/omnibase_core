# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidationRequest model — canonical input contract for a validation run.

Part of the Generic Validator Node Architecture (OMN-2362).

All validators and consumers of validation output must use these models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelValidationRequest(BaseModel):
    """Captures the target, scope, profile, and tag filters for a validation run.

    Example:
        >>> req = ModelValidationRequest(
        ...     target="src/omnibase_core/nodes/node_compute.py",
        ...     scope="file",
        ...     profile="default",
        ... )
        >>> req.scope
        'file'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    target: str = Field(
        description=(
            "Path, identifier, or artifact reference that this validation run targets. "
            "Interpretation depends on scope: a file path for 'file', a directory for "
            "'subtree', empty string or workspace root for 'workspace', or an artifact "
            "locator for 'artifact'."
        ),
    )

    scope: Literal["file", "subtree", "workspace", "artifact"] = Field(
        description=(
            "Breadth of the validation target. "
            "'file' — validate a single source file. "
            "'subtree' — validate all files under a directory tree. "
            "'workspace' — validate the entire repository workspace. "
            "'artifact' — validate a built or serialised artifact."
        ),
    )

    profile: Literal["strict", "default", "advisory"] = Field(
        default="default",
        description=(
            "Validation strictness profile. "
            "'strict' — WARN findings are elevated to FAIL when computing overall_status. "
            "'default' — findings are evaluated at face value. "
            "'advisory' — overall_status is never FAIL or ERROR; "
            "findings are informational only."
        ),
    )

    validator_ids: tuple[str, ...] = Field(
        default=(),
        description=(
            "Optional allow-list of validator IDs to run. "
            "When empty, all registered validators applicable to the target are run."
        ),
    )

    tag_filters: tuple[str, ...] = Field(
        default=(),
        description=(
            "Optional tag-based filter applied to the validator registry. "
            "Only validators whose tags intersect this set are included. "
            "Ignored when validator_ids is non-empty."
        ),
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Arbitrary caller-supplied key/value pairs forwarded to every validator "
            "invoked for this request. Useful for injecting build metadata, "
            "correlation IDs, or environment hints."
        ),
    )


__all__ = ["ModelValidationRequest"]

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidationFinding model — a single structured result from one validator.

Part of the Generic Validator Node Architecture (OMN-2362).

All findings must be structured; no free-form log strings as primary output.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelValidationFinding(BaseModel):
    """Captures a single result emitted by one validator during a validation run.

    Every finding is fully self-describing: it records which validator produced it,
    the severity, where the issue was found, a human-readable message, an optional
    remediation hint, and arbitrary structured evidence.

    Example:
        >>> finding = ModelValidationFinding(
        ...     validator_id="naming_convention",
        ...     severity="FAIL",
        ...     location="src/omnibase_core/nodes/node_bad.py:42",
        ...     message="Function 'doThing' does not follow snake_case convention.",
        ...     remediation="Rename to 'do_thing'.",
        ... )
        >>> finding.severity
        'FAIL'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    validator_id: str = Field(
        description=(
            "Unique identifier of the validator that produced this finding. "
            "Must match the validator_id on the corresponding ValidatorDescriptor."
        ),
    )

    severity: Literal["PASS", "WARN", "FAIL", "ERROR", "SKIP", "NOT_APPLICABLE"] = (
        Field(
            description=(
                "Severity of this individual finding. "
                "PASS — the validator ran and found no issue. "
                "WARN — potential issue that does not block in 'default' profile. "
                "FAIL — definite issue that blocks in 'default' and 'strict' profiles. "
                "ERROR — validator encountered an unexpected execution error. "
                "SKIP — validator intentionally skipped this target. "
                "NOT_APPLICABLE — validator does not apply to this target."
            ),
        )
    )

    location: str | None = Field(
        default=None,
        description=(
            "Human-readable location string indicating where the issue was found. "
            "Recommended format: 'path/to/file.py:line' or 'path/to/file.py:line:col'. "
            "May be None when location is not meaningful for the finding."
        ),
    )

    message: str = Field(
        description="Human-readable description of what the validator found.",
    )

    remediation: str | None = Field(
        default=None,
        description=(
            "Optional human-readable hint on how to fix the issue. "
            "Should be actionable and specific."
        ),
    )

    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Structured, machine-readable evidence supporting this finding. "
            "Content is validator-defined; consumers must not rely on specific keys "
            "without knowing the validator_id. "
            "Must be JSON-serialisable without custom encoders."
        ),
    )

    rule_id: str | None = Field(
        default=None,
        description=(
            "Optional identifier for the specific rule within the validator that "
            "produced this finding. Useful when a single validator enforces many rules."
        ),
    )


__all__ = ["ModelValidationFinding"]

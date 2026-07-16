# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validation status enum (unused by the OMN-14656 no_utcnow_check node).

This node originally forked a per-node ``ModelValidationReport`` /
``ModelValidationFinding`` pair keyed on this enum. OMN-14656 remediation
replaced that fork with the canonical OMN-2362 generic validator types
(:mod:`omnibase_core.models.validation.model_validation_report`,
:mod:`omnibase_core.models.validation.model_validation_finding`), whose
``severity``/``overall_status`` fields are an uppercase
``Literal["PASS", "WARN", "FAIL", "ERROR", "SKIP", "NOT_APPLICABLE"]`` (not
an enum) with precedence ERROR > FAIL > WARN > PASS computed by
``ModelValidationReport.from_findings()``. This enum is kept as a generated
artifact but is no longer referenced by ``node_no_utcnow_check_compute``.

Ticket: OMN-14656 (RSD canary — no_utcnow_check COMPUTE node).
"""

from enum import Enum

__all__ = ["EnumValidationStatus"]


class EnumValidationStatus(str, Enum):
    """Outcome status for a validation report or an individual finding.

    Attributes:
        PASS: The check (or overall report) passed.
        WARN: A non-blocking concern was detected.
        FAIL: A blocking violation was detected.
        ERROR: The check itself could not complete (e.g. a parse error).
        SKIP: The check was intentionally not executed.
        NOT_APPLICABLE: The check does not apply to this input.
    """

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"
    NOT_APPLICABLE = "not_applicable"

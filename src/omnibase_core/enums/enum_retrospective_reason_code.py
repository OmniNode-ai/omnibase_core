# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reason codes a retrospective verdict carries (OMN-21627)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumRetrospectiveReasonCode(UtilStrValueHelper, str, Enum):
    """Why an experiment evaluation did not pass. Unknown is never zero or a pass.

    Attributes:
        UNAUTHORIZED_EFFECT: Safety failure: an effect ran without authority.
        FALSE_COMPLETION: Safety failure: a completion claim was false.
        DUPLICATE_EFFECT: Safety failure: an external effect ran twice.
        CONTRACT_UNRESOLVED: The success contract still carries an unresolved value, which blocks evaluation.
        COHORT_UNRECONCILED: The cohort does not reconcile with its independent intake source.
        CAPTURE_BELOW_FLOOR: Capture coverage is below the floor needed to trust the measurement.
        WINDOW_NOT_MATURE: The observation window has not matured.
        VERDICT_UNRESOLVED: A required per-unit verdict is unknown or disputed.
        BASELINE_MISSING: The baseline snapshot is missing.
        ZERO_DENOMINATOR: The metric denominator is zero.
        PRIMARY_TARGET_MISSED: Mature evidence misses the primary target.
        COVERAGE_GUARDRAIL_FAILED: Mature evidence misses the operational coverage target.
        COST_GUARDRAIL_FAILED: Mature evidence breaks the cost guardrail.
        LATENCY_GUARDRAIL_FAILED: Mature evidence breaks the latency guardrail.
    """

    UNAUTHORIZED_EFFECT = "unauthorized_effect"
    FALSE_COMPLETION = "false_completion"
    DUPLICATE_EFFECT = "duplicate_effect"
    CONTRACT_UNRESOLVED = "contract_unresolved"
    COHORT_UNRECONCILED = "cohort_unreconciled"
    CAPTURE_BELOW_FLOOR = "capture_below_floor"
    WINDOW_NOT_MATURE = "window_not_mature"
    VERDICT_UNRESOLVED = "verdict_unresolved"
    BASELINE_MISSING = "baseline_missing"
    ZERO_DENOMINATOR = "zero_denominator"
    PRIMARY_TARGET_MISSED = "primary_target_missed"
    COVERAGE_GUARDRAIL_FAILED = "coverage_guardrail_failed"
    COST_GUARDRAIL_FAILED = "cost_guardrail_failed"
    LATENCY_GUARDRAIL_FAILED = "latency_guardrail_failed"

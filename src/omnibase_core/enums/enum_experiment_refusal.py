# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Operational refusals of the experiment loop (OMN-22001)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumExperimentRefusal(UtilStrValueHelper, str, Enum):
    """Why the experiment loop refused to proceed, as inherited from MASS and LPX.

    Distinct from the evaluator's reason codes (``EnumRetrospectiveReasonCode``):
    a refusal is a loop-level stop, and the evaluator code it implies is a table in
    the comparison compute's contract, not a property of this enum.

    Attributes:
        MISSING_EVIDENCE: Evidence the evaluation needs is absent.
        TASK_MISMATCH: The quality gate found the output does not match the task.
        REFUSED_UNMEASURED: A required quantity was never measured.
        REFUSED_NO_CONFIG_PIN: The run carries no pinned configuration.
        AA_CONTROL_FAILED: The A/A control did not hold.
        HELD_OUT_SPENT: The held-out set was already spent.
        STALE_DECISION: The decision was computed from superseded inputs.
        VOID: The experiment was voided.
        RULE_HASH_MISMATCH: The manifest's rule_sha does not match its values.
    """

    MISSING_EVIDENCE = "missing_evidence"
    TASK_MISMATCH = "task_mismatch"
    REFUSED_UNMEASURED = "refused_unmeasured"
    REFUSED_NO_CONFIG_PIN = "refused_no_config_pin"
    AA_CONTROL_FAILED = "aa_control_failed"
    HELD_OUT_SPENT = "held_out_spent"
    STALE_DECISION = "stale_decision"
    VOID = "void"
    RULE_HASH_MISMATCH = "rule_hash_mismatch"

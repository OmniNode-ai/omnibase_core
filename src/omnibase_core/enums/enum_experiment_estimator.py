# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Estimator a manifest declares, which the comparison compute dispatches on (OMN-22001)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumExperimentEstimator(UtilStrValueHelper, str, Enum):
    """No subject's estimator is replaced by another's.

    Attributes:
        PAIRED_BOOTSTRAP: MASS task-level paired bootstrap with the A/A control
            (``delegation_workflow`` subjects).
        CLUSTER_STRATIFIED: LPX cluster-stratified independent-arm comparison with
            the equal-budget retry arm (``lane_process`` subjects).
        BASELINE_THRESHOLD: Baseline-threshold evaluation (prototype and
            retrospective subjects).
    """

    PAIRED_BOOTSTRAP = "paired_bootstrap"
    CLUSTER_STRATIFIED = "cluster_stratified"
    BASELINE_THRESHOLD = "baseline_threshold"

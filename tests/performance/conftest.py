# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Performance test configuration for CI-aware threshold calibration.

Self-hosted runners share hardware across multiple concurrent jobs, which causes
15-25% lower throughput compared to dedicated GitHub-hosted runners. This module
provides a threshold multiplier that relaxes performance assertions in shared
runner environments.

Environment Variables:
    CI_RUNNER_TYPE: Runner environment type. Values:
        - "self-hosted": Shared hardware, apply relaxed thresholds (1.5x)
        - "github-hosted" or unset: Dedicated runners, use baseline thresholds

    CI: Standard CI flag. When "true" and CI_RUNNER_TYPE is unset, a moderate
        multiplier (1.25x) is applied to account for general CI variance.

Related:
    - OMN-3327: Calibrate performance test thresholds for self-hosted runner environment
    - OMN-3273: Self-hosted runner rollout
"""

import os

import pytest


def get_perf_threshold_multiplier() -> float:
    """Return a multiplier for performance thresholds based on runner environment.

    Returns:
        1.0 for local development (baseline).
        1.25 for generic CI (GitHub-hosted or unknown CI).
        1.5 for self-hosted runners (shared hardware, 5+ concurrent jobs).
    """
    runner_type = os.environ.get("CI_RUNNER_TYPE", "").lower()

    if runner_type == "self-hosted":
        return 1.5

    if os.environ.get("CI", "").lower() == "true":
        return 1.25

    return 1.0


def ci_threshold(baseline: float) -> float:
    """Scale a performance threshold for the current runner environment.

    Args:
        baseline: The baseline threshold value (calibrated for dedicated runners).

    Returns:
        The adjusted threshold, scaled by the runner-environment multiplier.

    Example:
        >>> assert throughput > ci_threshold(1000.0)  # 1000 on local, 667 on self-hosted
    """
    multiplier = get_perf_threshold_multiplier()
    return baseline / multiplier


def ci_upper_threshold(baseline: float) -> float:
    """Scale an upper-bound performance threshold for the current runner environment.

    Use this for thresholds where the assertion checks that a value is LESS THAN
    the threshold (e.g., ``assert time < threshold``). The threshold is multiplied
    (made more lenient) in CI environments.

    Args:
        baseline: The baseline upper-bound threshold (calibrated for dedicated runners).

    Returns:
        The adjusted threshold, scaled up by the runner-environment multiplier.

    Example:
        >>> assert total_time < ci_upper_threshold(1.0)  # 1.0s local, 1.5s self-hosted
    """
    multiplier = get_perf_threshold_multiplier()
    return baseline * multiplier


@pytest.fixture
def perf_multiplier() -> float:
    """Pytest fixture exposing the performance threshold multiplier.

    Returns:
        The multiplier for the current runner environment.
    """
    return get_perf_threshold_multiplier()

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Infrastructure & System Models

Models for system infrastructure, execution, and operational concerns.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.core.model_action_payload import ModelActionPayload
    from omnibase_core.models.infrastructure.model_compute_cache import (
        ModelComputeCache,
    )

    from .model_cli_result_data import ModelCliResultData
    from .model_duration import ModelDuration
    from .model_environment_variables import ModelEnvironmentVariables
    from .model_execution_summary import ModelExecutionSummary
    from .model_load_balancer_stats import ModelLoadBalancerStats
    from .model_metric import ModelMetric
    from .model_metrics_data import ModelMetricsData
    from .model_progress import ModelProgress
    from .model_protocol_action import ModelAction
    from .model_result import ModelResult, collect_results, err, ok, try_result
    from .model_result_dict import ModelResultData, ModelResultDict
    from .model_retry_policy import ModelRetryPolicy
    from .model_test_result import ModelTestResult
    from .model_test_results import ModelTestResults
    from .model_time_based import ModelTimeBased
    from .model_timeout import ModelTimeout
    from .model_timeout_data import ModelTimeoutData
    from .model_transaction import ModelTransaction

__all__ = [
    "ModelAction",
    "ModelActionPayload",
    "ModelComputeCache",
    "ModelCliResultData",
    "ModelDuration",
    "ModelEnvironmentVariables",
    "ModelExecutionSummary",
    "ModelMetric",
    "ModelMetricsData",
    "ModelProgress",
    "ModelResult",
    "ModelResultData",
    "ModelResultDict",
    "ModelRetryPolicy",
    "ModelTestResult",
    "ModelTestResults",
    "ModelTimeBased",
    "ModelTimeout",
    "ModelTimeoutData",
    "ModelTransaction",
    "ModelLoadBalancerStats",
    "collect_results",
    "err",
    "ok",
    "try_result",
]

# NOTE: Circular import workaround removed
# Previously, infrastructure layer imported ModelMetadataValue from metadata layer,
# creating circular dependency. Now using ModelFlexibleValue from common layer instead.
# This follows ONEX layered architecture: both infrastructure and metadata depend on common,
# not on each other.


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelActionPayload": (
        "omnibase_core.models.core.model_action_payload",
        "ModelActionPayload",
    ),
    "ModelComputeCache": (
        "omnibase_core.models.infrastructure.model_compute_cache",
        "ModelComputeCache",
    ),
    "ModelCliResultData": (
        "omnibase_core.models.infrastructure.model_cli_result_data",
        "ModelCliResultData",
    ),
    "ModelDuration": (
        "omnibase_core.models.infrastructure.model_duration",
        "ModelDuration",
    ),
    "ModelEnvironmentVariables": (
        "omnibase_core.models.infrastructure.model_environment_variables",
        "ModelEnvironmentVariables",
    ),
    "ModelExecutionSummary": (
        "omnibase_core.models.infrastructure.model_execution_summary",
        "ModelExecutionSummary",
    ),
    "ModelLoadBalancerStats": (
        "omnibase_core.models.infrastructure.model_load_balancer_stats",
        "ModelLoadBalancerStats",
    ),
    "ModelMetric": ("omnibase_core.models.infrastructure.model_metric", "ModelMetric"),
    "ModelMetricsData": (
        "omnibase_core.models.infrastructure.model_metrics_data",
        "ModelMetricsData",
    ),
    "ModelProgress": (
        "omnibase_core.models.infrastructure.model_progress",
        "ModelProgress",
    ),
    "ModelAction": (
        "omnibase_core.models.infrastructure.model_protocol_action",
        "ModelAction",
    ),
    "ModelResult": ("omnibase_core.models.infrastructure.model_result", "ModelResult"),
    "collect_results": (
        "omnibase_core.models.infrastructure.model_result",
        "collect_results",
    ),
    "err": ("omnibase_core.models.infrastructure.model_result", "err"),
    "ok": ("omnibase_core.models.infrastructure.model_result", "ok"),
    "try_result": ("omnibase_core.models.infrastructure.model_result", "try_result"),
    "ModelResultData": (
        "omnibase_core.models.infrastructure.model_result_dict",
        "ModelResultData",
    ),
    "ModelResultDict": (
        "omnibase_core.models.infrastructure.model_result_dict",
        "ModelResultDict",
    ),
    "ModelRetryPolicy": (
        "omnibase_core.models.infrastructure.model_retry_policy",
        "ModelRetryPolicy",
    ),
    "ModelTestResult": (
        "omnibase_core.models.infrastructure.model_test_result",
        "ModelTestResult",
    ),
    "ModelTestResults": (
        "omnibase_core.models.infrastructure.model_test_results",
        "ModelTestResults",
    ),
    "ModelTimeBased": (
        "omnibase_core.models.infrastructure.model_time_based",
        "ModelTimeBased",
    ),
    "ModelTimeout": (
        "omnibase_core.models.infrastructure.model_timeout",
        "ModelTimeout",
    ),
    "ModelTimeoutData": (
        "omnibase_core.models.infrastructure.model_timeout_data",
        "ModelTimeoutData",
    ),
    "ModelTransaction": (
        "omnibase_core.models.infrastructure.model_transaction",
        "ModelTransaction",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})

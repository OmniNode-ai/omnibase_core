"""
Infrastructure & System Models

Models for system infrastructure, execution, and operational concerns.
"""

from omnibase_core.models.core.model_action_payload import ModelActionPayload
from omnibase_core.models.infrastructure.model_compute_cache import ModelComputeCache

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

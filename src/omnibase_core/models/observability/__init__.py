# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Observability emission models and cardinality policies.

This module provides models for metrics emission, log emission,
and cardinality policy enforcement for the ONEX observability stack.

Metrics Emission Models:
    - ModelCounterEmission: Counter metric increments
    - ModelGaugeEmission: Gauge metric values
    - ModelHistogramObservation: Histogram observations

Log Emission:
    - ModelLogEmission: Structured log entries with severity

Cardinality Policy:
    - ModelMetricsPolicy: Label validation and cardinality enforcement
    - ModelLabelViolation: Individual policy violation details
    - ModelLabelValidationResult: Complete validation result with sanitization

Envelope Validation Metrics:
    - ModelEnvelopeValidationTimingMetrics: p50/p95/p99 latency with per-step breakdown
    - ModelEnvelopeValidationFailureMetrics: Per-type failure rates and alerting
    - ModelEnvelopeValidationSummary: Combined timing and failure snapshot
"""

from omnibase_core.models.observability.model_counter_emission import (
    ModelCounterEmission,
)
from omnibase_core.models.observability.model_envelope_validation_failure_metrics import (
    ModelEnvelopeValidationFailureMetrics,
)
from omnibase_core.models.observability.model_envelope_validation_summary import (
    ModelEnvelopeValidationSummary,
)
from omnibase_core.models.observability.model_envelope_validation_timing_metrics import (
    ModelEnvelopeValidationTimingMetrics,
)
from omnibase_core.models.observability.model_gauge_emission import ModelGaugeEmission
from omnibase_core.models.observability.model_histogram_observation import (
    ModelHistogramObservation,
)
from omnibase_core.models.observability.model_label_validation_result import (
    ModelLabelValidationResult,
)
from omnibase_core.models.observability.model_label_violation import ModelLabelViolation
from omnibase_core.models.observability.model_log_emission import ModelLogEmission
from omnibase_core.models.observability.model_metrics_policy import ModelMetricsPolicy

__all__ = [
    # Metrics emission
    "ModelCounterEmission",
    "ModelGaugeEmission",
    "ModelHistogramObservation",
    # Log emission
    "ModelLogEmission",
    # Cardinality policy
    "ModelMetricsPolicy",
    "ModelLabelViolation",
    "ModelLabelValidationResult",
    # Envelope validation metrics
    "ModelEnvelopeValidationTimingMetrics",
    "ModelEnvelopeValidationFailureMetrics",
    "ModelEnvelopeValidationSummary",
]

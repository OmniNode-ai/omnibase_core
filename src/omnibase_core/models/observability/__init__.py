# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Observability emission models and cardinality policies.

Models for metrics emission, log emission,
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

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    from omnibase_core.models.observability.model_gauge_emission import (
        ModelGaugeEmission,
    )
    from omnibase_core.models.observability.model_histogram_observation import (
        ModelHistogramObservation,
    )
    from omnibase_core.models.observability.model_label_validation_result import (
        ModelLabelValidationResult,
    )
    from omnibase_core.models.observability.model_label_violation import (
        ModelLabelViolation,
    )
    from omnibase_core.models.observability.model_log_emission import ModelLogEmission
    from omnibase_core.models.observability.model_metrics_policy import (
        ModelMetricsPolicy,
    )

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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelCounterEmission": (
        "omnibase_core.models.observability.model_counter_emission",
        "ModelCounterEmission",
    ),
    "ModelEnvelopeValidationFailureMetrics": (
        "omnibase_core.models.observability.model_envelope_validation_failure_metrics",
        "ModelEnvelopeValidationFailureMetrics",
    ),
    "ModelEnvelopeValidationSummary": (
        "omnibase_core.models.observability.model_envelope_validation_summary",
        "ModelEnvelopeValidationSummary",
    ),
    "ModelEnvelopeValidationTimingMetrics": (
        "omnibase_core.models.observability.model_envelope_validation_timing_metrics",
        "ModelEnvelopeValidationTimingMetrics",
    ),
    "ModelGaugeEmission": (
        "omnibase_core.models.observability.model_gauge_emission",
        "ModelGaugeEmission",
    ),
    "ModelHistogramObservation": (
        "omnibase_core.models.observability.model_histogram_observation",
        "ModelHistogramObservation",
    ),
    "ModelLabelValidationResult": (
        "omnibase_core.models.observability.model_label_validation_result",
        "ModelLabelValidationResult",
    ),
    "ModelLabelViolation": (
        "omnibase_core.models.observability.model_label_violation",
        "ModelLabelViolation",
    ),
    "ModelLogEmission": (
        "omnibase_core.models.observability.model_log_emission",
        "ModelLogEmission",
    ),
    "ModelMetricsPolicy": (
        "omnibase_core.models.observability.model_metrics_policy",
        "ModelMetricsPolicy",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})

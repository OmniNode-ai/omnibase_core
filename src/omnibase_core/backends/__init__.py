"""
Backends Module - Pluggable backend implementations.

This module provides backend implementations for various infrastructure
concerns like metrics, logging, and tracing. Backends implement protocols
defined in omnibase_core.protocols.

Module Organization:
    - metrics/: Metrics backend implementations (Prometheus, In-Memory, etc.)

Usage:
    from omnibase_core.backends.metrics import (
        BackendMetricsInMemory,
        BackendMetricsPrometheus,
    )

.. versionadded:: 0.5.7
"""

from omnibase_core.backends.metrics import (
    BackendMetricsInMemory,
)

__all__ = [
    "BackendMetricsInMemory",
]

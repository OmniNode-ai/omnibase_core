# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Metrics Protocol Module - Backend abstractions for metrics collection.

Protocol definitions for metrics backends,
enabling pluggable metrics implementations (Prometheus, StatsD, OpenTelemetry, etc.)
while maintaining a consistent interface.

Usage:
    from omnibase_core.protocols.metrics import ProtocolMetricsBackend

    class MyBackend:
        '''Custom metrics backend implementation.'''

        def record_gauge(
            self, name: str, value: float, tags: dict[str, str] | None = None
        ) -> None:
            # Custom implementation
            pass

        def increment_counter(
            self, name: str, value: float = 1.0, tags: dict[str, str] | None = None
        ) -> None:
            # Custom implementation
            pass

        def record_histogram(
            self, name: str, value: float, tags: dict[str, str] | None = None
        ) -> None:
            # Custom implementation
            pass

        def push(self) -> None:
            # Push metrics to remote (optional)
            pass

.. versionadded:: 0.5.7
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.metrics.protocol_metrics_backend import (
        ProtocolMetricsBackend,
    )

__all__ = [
    "ProtocolMetricsBackend",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolMetricsBackend": (
        "omnibase_core.protocols.metrics.protocol_metrics_backend",
        "ProtocolMetricsBackend",
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

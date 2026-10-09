# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Compute protocols for NodeCompute dependency injection.

These protocols enable dependency inversion for NodeCompute infrastructure
concerns (caching, timing, parallel execution, circuit breaking, monitoring) per OMN-700.

Protocols:
    - ProtocolComputeCache: Cache interface for computation results
    - ProtocolTimingService: Timing/metrics interface
    - ProtocolParallelExecutor: Parallel execution interface
    - ProtocolCircuitBreaker: Sync circuit breaker interface (OMN-861)
    - ProtocolAsyncCircuitBreaker: Async circuit breaker interface (OMN-861)
    - ProtocolPerformanceMonitor: Performance monitoring interface (OMN-848)

.. versionadded:: 0.4.0
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.compute.protocol_circuit_breaker import (
        ProtocolAsyncCircuitBreaker,
        ProtocolCircuitBreaker,
    )
    from omnibase_core.protocols.compute.protocol_compute_cache import (
        ProtocolComputeCache,
    )
    from omnibase_core.protocols.compute.protocol_parallel_executor import (
        ProtocolParallelExecutor,
    )
    from omnibase_core.protocols.compute.protocol_payload_data import (
        ProtocolComputePayloadData,
        ProtocolDictLike,
    )
    from omnibase_core.protocols.compute.protocol_performance_monitor import (
        ProtocolPerformanceMonitor,
    )
    from omnibase_core.protocols.compute.protocol_timing_service import (
        ProtocolTimingService,
    )
    from omnibase_core.protocols.compute.protocol_tool_cache import ProtocolToolCache

__all__ = [
    "ProtocolAsyncCircuitBreaker",
    "ProtocolCircuitBreaker",
    "ProtocolComputeCache",
    "ProtocolComputePayloadData",
    "ProtocolDictLike",
    "ProtocolParallelExecutor",
    "ProtocolPerformanceMonitor",
    "ProtocolTimingService",
    "ProtocolToolCache",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolAsyncCircuitBreaker": (
        "omnibase_core.protocols.compute.protocol_circuit_breaker",
        "ProtocolAsyncCircuitBreaker",
    ),
    "ProtocolCircuitBreaker": (
        "omnibase_core.protocols.compute.protocol_circuit_breaker",
        "ProtocolCircuitBreaker",
    ),
    "ProtocolComputeCache": (
        "omnibase_core.protocols.compute.protocol_compute_cache",
        "ProtocolComputeCache",
    ),
    "ProtocolParallelExecutor": (
        "omnibase_core.protocols.compute.protocol_parallel_executor",
        "ProtocolParallelExecutor",
    ),
    "ProtocolComputePayloadData": (
        "omnibase_core.protocols.compute.protocol_payload_data",
        "ProtocolComputePayloadData",
    ),
    "ProtocolDictLike": (
        "omnibase_core.protocols.compute.protocol_payload_data",
        "ProtocolDictLike",
    ),
    "ProtocolPerformanceMonitor": (
        "omnibase_core.protocols.compute.protocol_performance_monitor",
        "ProtocolPerformanceMonitor",
    ),
    "ProtocolTimingService": (
        "omnibase_core.protocols.compute.protocol_timing_service",
        "ProtocolTimingService",
    ),
    "ProtocolToolCache": (
        "omnibase_core.protocols.compute.protocol_tool_cache",
        "ProtocolToolCache",
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

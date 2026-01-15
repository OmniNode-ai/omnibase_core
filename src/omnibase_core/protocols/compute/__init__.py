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

from omnibase_core.protocols.compute.protocol_circuit_breaker import (
    ProtocolAsyncCircuitBreaker,
    ProtocolCircuitBreaker,
)
from omnibase_core.protocols.compute.protocol_compute_cache import ProtocolComputeCache
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

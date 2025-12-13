"""
Compute protocols for NodeCompute dependency injection.

These protocols enable dependency inversion for NodeCompute infrastructure
concerns (caching, timing, parallel execution) per OMN-700.

Protocols:
    - ProtocolComputeCache: Cache interface for computation results
    - ProtocolTimingService: Timing/metrics interface
    - ProtocolParallelExecutor: Parallel execution interface

.. versionadded:: 0.4.0
"""

from omnibase_core.protocols.compute.protocol_compute_cache import ProtocolComputeCache
from omnibase_core.protocols.compute.protocol_parallel_executor import (
    ProtocolParallelExecutor,
)
from omnibase_core.protocols.compute.protocol_timing_service import (
    ProtocolTimingService,
)

__all__ = [
    "ProtocolComputeCache",
    "ProtocolParallelExecutor",
    "ProtocolTimingService",
]

"""
Replay infrastructure injectors and executor.

This module provides implementations for deterministic replay:

- **ServiceRNGInjector**: RNG injection for deterministic replay (from services.replay)
- **ServiceTimeInjector**: Time injection for deterministic replay (from services.replay)
- **ServiceEffectRecorder**: Effect recording and replay for determinism (from services.replay)
- **ExecutorReplay**: Replay executor orchestrating deterministic execution
- **ReplaySession**: Active replay session with injected services

Note:
    ServiceRNGInjector, ServiceTimeInjector, and ServiceEffectRecorder are now located in
    omnibase_core.services.replay and re-exported here for convenience.
    For direct imports, use:

        from omnibase_core.services.replay.service_rng_injector import ServiceRNGInjector
        from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector
        from omnibase_core.services.replay.service_effect_recorder import ServiceEffectRecorder

Usage:
    >>> from omnibase_core.pipeline.replay import (
    ...     ServiceRNGInjector, ServiceTimeInjector, ServiceEffectRecorder, ExecutorReplay, ReplaySession
    ... )
    >>> from omnibase_core.enums.replay import EnumRecorderMode
    >>> from datetime import datetime, timezone
    >>>
    >>> # RNG injection
    >>> rng = ServiceRNGInjector(seed=42)
    >>> value = rng.random()
    >>>
    >>> # Time injection
    >>> fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    >>> time_svc = ServiceTimeInjector(fixed_time=fixed)
    >>> time_svc.now()
    datetime.datetime(2024, 6, 15, 12, 0, tzinfo=datetime.timezone.utc)
    >>>
    >>> # Effect recording
    >>> recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING, time_service=time_svc)
    >>> record = recorder.record("http.get", {"url": "..."}, {"status": 200})
    >>>
    >>> # Replay executor
    >>> executor = ExecutorReplay()
    >>> session = executor.create_recording_session(rng_seed=42)
    >>> manifest = executor.capture_manifest(session)

.. versionadded:: 0.4.0
    Added Replay Infrastructure (OMN-1116)
"""

from omnibase_core.pipeline.replay.runner_replay_executor import ExecutorReplay
from omnibase_core.pipeline.replay.runner_replay_session import ReplaySession
from omnibase_core.services.replay.service_effect_recorder import ServiceEffectRecorder
from omnibase_core.services.replay.service_rng_injector import ServiceRNGInjector
from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector

__all__ = [
    "ExecutorReplay",
    "ServiceRNGInjector",
    "ServiceTimeInjector",
    "ServiceEffectRecorder",
    "ReplaySession",
]

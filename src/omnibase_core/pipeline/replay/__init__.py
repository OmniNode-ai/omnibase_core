# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Replay infrastructure injectors, recorders, and executor.

This module provides implementations for deterministic replay:

- **InjectorRNG**: RNG injection for deterministic replay
- **InjectorTime**: Time injection for deterministic replay
- **RecorderEffect**: Effect recording and replay for determinism
- **ExecutorReplay**: Replay executor orchestrating deterministic execution
- **ReplaySession**: Active replay session with injected services

Usage:
    >>> from omnibase_core.pipeline.replay import (
    ...     InjectorRNG, InjectorTime, RecorderEffect, ExecutorReplay, ReplaySession
    ... )
    >>> from omnibase_core.enums.replay import EnumRecorderMode
    >>> from datetime import datetime, timezone
    >>>
    >>> # RNG injection
    >>> rng = InjectorRNG(seed=42)
    >>> value = rng.random()
    >>>
    >>> # Time injection
    >>> fixed = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    >>> time_svc = InjectorTime(fixed_time=fixed)
    >>> time_svc.now()
    datetime.datetime(2024, 6, 15, 12, 0, tzinfo=datetime.timezone.utc)
    >>>
    >>> # Effect recording
    >>> recorder = RecorderEffect(mode=EnumRecorderMode.RECORDING, time_service=time_svc)
    >>> record = recorder.record("http.get", {"url": "..."}, {"status": 200})
    >>>
    >>> # Replay executor
    >>> executor = ExecutorReplay()
    >>> session = executor.create_recording_session(rng_seed=42)
    >>> manifest = executor.capture_manifest(session)

.. versionadded:: 0.4.0
    Added Replay Infrastructure (OMN-1116)
"""

from omnibase_core.pipeline.replay.executor_replay import ExecutorReplay
from omnibase_core.pipeline.replay.injector_rng import InjectorRNG
from omnibase_core.pipeline.replay.injector_time import InjectorTime
from omnibase_core.pipeline.replay.recorder_effect import RecorderEffect
from omnibase_core.pipeline.replay.session_replay import ReplaySession

__all__ = [
    "ExecutorReplay",
    "InjectorRNG",
    "InjectorTime",
    "RecorderEffect",
    "ReplaySession",
]

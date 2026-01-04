# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
RecorderEffect - Effect recorder for deterministic replay.

This module provides the default ProtocolEffectRecorder implementation for
capturing and replaying effects in the ONEX pipeline.

Design:
    The recorder supports three modes:
    - PASS_THROUGH: Effects execute normally (production mode)
    - RECORDING: Effects execute and results are captured for later replay
    - REPLAYING: Effects return pre-recorded results instead of executing

Architecture:
    During recording, each effect execution is captured as a ModelEffectRecord
    with its intent (input) and result (output). The sequence index maintains
    execution order. During replay, the recorder matches effect_type and intent
    to return the pre-recorded result.

Usage:
    .. code-block:: python

        from omnibase_core.pipeline.replay import RecorderEffect
        from omnibase_core.enums.replay import EnumRecorderMode

        # Production mode (default): pass-through, no recording
        prod_recorder = RecorderEffect()

        # Recording mode: capture effect executions
        recording_recorder = RecorderEffect(mode=EnumRecorderMode.RECORDING)
        record = recording_recorder.record(
            effect_type="http.get",
            intent={"url": "https://api.example.com"},
            result={"status_code": 200, "body": {"data": "value"}},
        )

        # Replay mode: return pre-recorded results
        records = recording_recorder.get_all_records()
        replay_recorder = RecorderEffect(
            mode=EnumRecorderMode.REPLAYING,
            records=records,
        )
        result = replay_recorder.get_replay_result(
            effect_type="http.get",
            intent={"url": "https://api.example.com"},
        )
        # result == {"status_code": 200, "body": {"data": "value"}}

Key Invariant:
    Recording + Replay -> Same results (determinism)

    .. code-block:: python

        # Record
        recorder = RecorderEffect(mode=EnumRecorderMode.RECORDING)
        recorder.record("http.get", intent, result)
        records = recorder.get_all_records()

        # Replay
        replay = RecorderEffect(mode=EnumRecorderMode.REPLAYING, records=records)
        replayed_result = replay.get_replay_result("http.get", intent)
        assert replayed_result == result

Thread Safety:
    RecorderEffect uses a list for internal storage. While the ModelEffectRecord
    instances are immutable (frozen), concurrent recording from multiple threads
    is NOT safe. Use thread-local recorders or external synchronization if
    concurrent recording is needed.

Related:
    - OMN-1116: Implement Effect Recorder for Replay Infrastructure
    - ProtocolEffectRecorder: Protocol definition
    - ModelEffectRecord: Effect record model
    - InjectorTime: Time service for timestamps

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["RecorderEffect"]

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from omnibase_core.enums.replay.enum_recorder_mode import EnumRecorderMode
from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
from omnibase_core.protocols.replay.protocol_effect_recorder import (
    ProtocolEffectRecorder,
)
from omnibase_core.types.type_json import JsonType

if TYPE_CHECKING:
    from omnibase_core.protocols.replay.protocol_time_service import ProtocolTimeService


class RecorderEffect:
    """
    Effect recorder for deterministic replay.

    Captures effect intents and results during recording mode, and returns
    pre-recorded results during replay mode. In pass-through mode (default),
    no recording or replay occurs.

    Args:
        mode: Operating mode (PASS_THROUGH, RECORDING, or REPLAYING).
            Defaults to PASS_THROUGH for production use.
        records: Pre-recorded effects for replay mode. Only used when
            mode is REPLAYING. Defaults to empty list.
        time_service: Time service for timestamps. If None, uses current
            UTC time directly.

    Attributes:
        is_recording: Whether the recorder is in recording mode.
        is_replaying: Whether the recorder is in replay mode.

    Example:
        >>> from omnibase_core.pipeline.replay.recorder_effect import RecorderEffect
        >>> from omnibase_core.enums.replay import EnumRecorderMode
        >>> # Production mode (default)
        >>> recorder = RecorderEffect()
        >>> recorder.is_recording
        False
        >>> recorder.is_replaying
        False
        >>>
        >>> # Recording mode
        >>> recorder = RecorderEffect(mode=EnumRecorderMode.RECORDING)
        >>> recorder.is_recording
        True

    Thread Safety:
        Not thread-safe for concurrent recording. Use thread-local instances
        or external synchronization for multi-threaded recording.

    .. versionadded:: 0.4.0
    """

    def __init__(
        self,
        mode: EnumRecorderMode = EnumRecorderMode.PASS_THROUGH,
        records: list[ModelEffectRecord] | None = None,
        time_service: ProtocolTimeService | None = None,
    ) -> None:
        """
        Initialize the effect recorder.

        Args:
            mode: Operating mode. Defaults to PASS_THROUGH.
            records: Pre-recorded effects for replay mode.
            time_service: Time service for timestamps.
        """
        self._mode = mode
        self._records: list[ModelEffectRecord] = list(records) if records else []
        self._sequence_counter = 0
        self._time_service = time_service
        self._replay_index = 0  # For sequential replay

    @property
    def is_recording(self) -> bool:
        """
        Return whether the recorder is in recording mode.

        Returns:
            bool: True if in recording mode, False otherwise.

        Example:
            >>> recorder = RecorderEffect(mode=EnumRecorderMode.RECORDING)
            >>> recorder.is_recording
            True
        """
        return self._mode == EnumRecorderMode.RECORDING

    @property
    def is_replaying(self) -> bool:
        """
        Return whether the recorder is in replay mode.

        Returns:
            bool: True if in replay mode, False otherwise.

        Example:
            >>> recorder = RecorderEffect(mode=EnumRecorderMode.REPLAYING, records=[])
            >>> recorder.is_replaying
            True
        """
        return self._mode == EnumRecorderMode.REPLAYING

    def _get_current_time(self) -> datetime:
        """
        Get the current time from the time service or system.

        Returns:
            datetime: Current UTC time.
        """
        if self._time_service is not None:
            return self._time_service.now()
        return datetime.now(UTC)

    def record(
        self,
        effect_type: str,
        intent: dict[str, JsonType],
        result: dict[str, JsonType],
        success: bool = True,
        error_message: str | None = None,
    ) -> ModelEffectRecord:
        """
        Record an effect execution.

        Creates a ModelEffectRecord capturing the effect intent and result.
        Only records in RECORDING mode; in other modes, creates a record
        but does not store it.

        Args:
            effect_type: Identifier for the effect type.
            intent: What was requested (input parameters).
            result: What happened (output data).
            success: Whether the effect succeeded. Defaults to True.
            error_message: Error message if failed. Defaults to None.

        Returns:
            ModelEffectRecord: The created effect record.

        Example:
            >>> recorder = RecorderEffect(mode=EnumRecorderMode.RECORDING)
            >>> record = recorder.record(
            ...     effect_type="http.get",
            ...     intent={"url": "https://api.example.com"},
            ...     result={"status_code": 200},
            ... )
            >>> record.sequence_index
            0
        """
        record = ModelEffectRecord(
            effect_type=effect_type,
            intent=intent,
            result=result,
            captured_at=self._get_current_time(),
            sequence_index=self._sequence_counter,
            success=success,
            error_message=error_message,
        )

        if self._mode == EnumRecorderMode.RECORDING:
            self._records.append(record)
            self._sequence_counter += 1

        return record

    def get_replay_result(
        self, effect_type: str, intent: dict[str, JsonType]
    ) -> dict[str, JsonType] | None:
        """
        Get pre-recorded result for replay.

        Searches for a record matching the effect_type and intent exactly.
        Only works in REPLAYING mode; returns None in other modes.

        Args:
            effect_type: Identifier for the effect type.
            intent: What was requested (must match exactly).

        Returns:
            dict[str, JsonType] | None: Pre-recorded result if found, None otherwise.

        Example:
            >>> records = [...]  # Pre-recorded effects
            >>> recorder = RecorderEffect(
            ...     mode=EnumRecorderMode.REPLAYING,
            ...     records=records,
            ... )
            >>> result = recorder.get_replay_result(
            ...     effect_type="http.get",
            ...     intent={"url": "https://api.example.com"},
            ... )
        """
        if self._mode != EnumRecorderMode.REPLAYING:
            return None

        # Search for matching record by effect_type and intent
        for record in self._records:
            if record.effect_type == effect_type and record.intent == intent:
                return record.result

        return None

    def get_all_records(self) -> list[ModelEffectRecord]:
        """
        Return all recorded effects.

        Returns a copy of the internal records list to prevent external
        modification of internal state.

        Returns:
            list[ModelEffectRecord]: Copy of all recorded effects.

        Example:
            >>> recorder = RecorderEffect(mode=EnumRecorderMode.RECORDING)
            >>> recorder.record("http.get", {"url": "..."}, {"status": 200})
            >>> records = recorder.get_all_records()
            >>> len(records)
            1
        """
        return list(self._records)


# Verify protocol compliance at module load time
_recorder_check: ProtocolEffectRecorder = RecorderEffect()

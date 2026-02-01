"""
ServiceEffectRecorder - Effect recorder for deterministic replay.

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

        from omnibase_core.services.replay.service_effect_recorder import ServiceEffectRecorder
        from omnibase_core.enums.replay import EnumRecorderMode

        # Production mode (default): pass-through, no recording
        prod_recorder = ServiceEffectRecorder()

        # Recording mode: capture effect executions
        recording_recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
        record = recording_recorder.record(
            effect_type="http.get",
            intent={"url": "https://api.example.com"},
            result={"status_code": 200, "body": {"data": "value"}},
        )

        # Replay mode: return pre-recorded results
        records = recording_recorder.get_all_records()
        replay_recorder = ServiceEffectRecorder(
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
        recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
        recorder.record("http.get", intent, result)
        records = recorder.get_all_records()

        # Replay
        replay = ServiceEffectRecorder(mode=EnumRecorderMode.REPLAYING, records=records)
        replayed_result = replay.get_replay_result("http.get", intent)
        assert replayed_result == result

Thread Safety:
    ServiceEffectRecorder uses a list for internal storage. While the ModelEffectRecord
    instances are immutable (frozen), concurrent recording from multiple threads
    is NOT safe. Use thread-local recorders or external synchronization if
    concurrent recording is needed.

Related:
    - OMN-1116: Implement Effect Recorder for Replay Infrastructure
    - ProtocolEffectRecorder: Protocol definition
    - ModelEffectRecord: Effect record model
    - ServiceTimeInjector: Time service for timestamps

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ServiceEffectRecorder"]

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.replay.enum_recorder_mode import EnumRecorderMode
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
from omnibase_core.protocols.replay.protocol_effect_recorder import (
    ProtocolEffectRecorder,
)
from omnibase_core.types.type_json import JsonType

if TYPE_CHECKING:
    from omnibase_core.protocols.replay.protocol_time_service import ProtocolTimeService


class ServiceEffectRecorder:
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
        >>> from omnibase_core.services.replay.service_effect_recorder import ServiceEffectRecorder
        >>> from omnibase_core.enums.replay import EnumRecorderMode
        >>> # Production mode (default)
        >>> recorder = ServiceEffectRecorder()
        >>> recorder.is_recording
        False
        >>> recorder.is_replaying
        False
        >>>
        >>> # Recording mode
        >>> recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
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

        # Build O(1) lookup index for replay mode (avoids O(n) linear search)
        # Key: (effect_type, canonical_intent_json) -> record
        self._replay_lookup: dict[tuple[str, str], ModelEffectRecord] = {}
        if mode == EnumRecorderMode.REPLAYING:
            self._build_replay_index()

    @property
    def is_recording(self) -> bool:
        """
        Return whether the recorder is in recording mode.

        Returns:
            bool: True if in recording mode, False otherwise.

        Example:
            >>> recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
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
            >>> recorder = ServiceEffectRecorder(mode=EnumRecorderMode.REPLAYING, records=[])
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

    def _intent_key(self, intent: dict[str, JsonType]) -> str:
        """
        Create a hashable key from intent dict for O(1) lookup.

        Uses canonical JSON serialization with sorted keys for deterministic
        hashing of intent dictionaries.

        Args:
            intent: The intent dict to create a key for.

        Returns:
            str: Canonical JSON string representation.
        """
        return json.dumps(intent, sort_keys=True, separators=(",", ":"))

    def _build_replay_index(self) -> None:
        """
        Build O(1) lookup index from records for replay mode.

        Creates a dictionary mapping (effect_type, intent_key) -> record
        for fast replay lookups. Called once at initialization in REPLAYING mode.
        """
        for record in self._records:
            key = (record.effect_type, self._intent_key(record.intent))
            # First matching record wins (maintains original linear search behavior)
            if key not in self._replay_lookup:
                self._replay_lookup[key] = record

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
            >>> recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
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

    def _validate_effect_type(self, effect_type: str) -> None:
        """
        Validate that effect_type is non-empty.

        Args:
            effect_type: The effect type to validate.

        Raises:
            ModelOnexError: If effect_type is empty or whitespace-only.
        """
        if not effect_type or not effect_type.strip():
            raise ModelOnexError(
                message="effect_type must not be empty",
                error_code=EnumCoreErrorCode.REPLAY_INVALID_EFFECT_TYPE,
                effect_type=effect_type,
            )

    def get_replay_result(
        self, effect_type: str, intent: dict[str, JsonType]
    ) -> dict[str, JsonType] | None:
        """
        Get pre-recorded result for replay.

        Uses O(1) index lookup to find a record matching the effect_type and
        intent exactly. Only works in REPLAYING mode; returns None in other modes.

        Args:
            effect_type: Identifier for the effect type (must not be empty).
            intent: What was requested (must match exactly).

        Returns:
            dict[str, JsonType] | None: Pre-recorded result if found, None otherwise.

        Raises:
            ModelOnexError: If effect_type is empty (REPLAY_INVALID_EFFECT_TYPE).

        Example:
            >>> records = [...]  # Pre-recorded effects
            >>> recorder = ServiceEffectRecorder(
            ...     mode=EnumRecorderMode.REPLAYING,
            ...     records=records,
            ... )
            >>> result = recorder.get_replay_result(
            ...     effect_type="http.get",
            ...     intent={"url": "https://api.example.com"},
            ... )
        """
        # Validate input
        self._validate_effect_type(effect_type)

        if self._mode != EnumRecorderMode.REPLAYING:
            return None

        # O(1) lookup using pre-built index (instead of O(n) linear search)
        key = (effect_type, self._intent_key(intent))
        record = self._replay_lookup.get(key)
        return record.result if record is not None else None

    def require_replay_result(
        self, effect_type: str, intent: dict[str, JsonType]
    ) -> dict[str, JsonType]:
        """
        Get pre-recorded result for replay, raising on failure.

        This is a strict version of get_replay_result() that raises structured
        errors instead of returning None. Use this when replay failures should
        be treated as errors rather than graceful fallbacks.

        Args:
            effect_type: Identifier for the effect type (must not be empty).
            intent: What was requested (must match exactly).

        Returns:
            dict[str, JsonType]: The pre-recorded result.

        Raises:
            ModelOnexError: If effect_type is empty (REPLAY_INVALID_EFFECT_TYPE).
            ModelOnexError: If not in replay mode (REPLAY_NOT_IN_REPLAY_MODE).
            ModelOnexError: If no matching record found (REPLAY_RECORD_NOT_FOUND).

        Example:
            >>> records = [...]  # Pre-recorded effects
            >>> recorder = ServiceEffectRecorder(
            ...     mode=EnumRecorderMode.REPLAYING,
            ...     records=records,
            ... )
            >>> try:
            ...     result = recorder.require_replay_result(
            ...         effect_type="http.get",
            ...         intent={"url": "https://api.example.com"},
            ...     )
            ... except ModelOnexError as e:
            ...     print(f"Replay failed: {e.error_code}")
        """
        # Validate input
        self._validate_effect_type(effect_type)

        # Check mode
        if self._mode != EnumRecorderMode.REPLAYING:
            raise ModelOnexError(
                message=(
                    f"Cannot get replay result: recorder is in "
                    f"{self._mode.value} mode, not REPLAYING mode"
                ),
                error_code=EnumCoreErrorCode.REPLAY_NOT_IN_REPLAY_MODE,
                current_mode=self._mode.value,
                effect_type=effect_type,
            )

        # O(1) lookup using pre-built index
        key = (effect_type, self._intent_key(intent))
        record = self._replay_lookup.get(key)

        if record is None:
            # Provide helpful context about what was searched
            available_effect_types = sorted({et for et, _ in self._replay_lookup})
            raise ModelOnexError(
                message=f"No matching effect record found for effect_type='{effect_type}'",
                error_code=EnumCoreErrorCode.REPLAY_RECORD_NOT_FOUND,
                effect_type=effect_type,
                intent_keys=list(intent.keys()),
                available_effect_types=available_effect_types[:10],
                total_records=len(self._records),
            )

        return record.result

    def get_all_records(self) -> list[ModelEffectRecord]:
        """
        Return all recorded effects.

        Returns a copy of the internal records list to prevent external
        modification of internal state.

        Returns:
            list[ModelEffectRecord]: Copy of all recorded effects.

        Example:
            >>> recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
            >>> recorder.record("http.get", {"url": "..."}, {"status": 200})
            >>> records = recorder.get_all_records()
            >>> len(records)
            1
        """
        return list(self._records)

    def iter_records(self) -> Iterator[ModelEffectRecord]:
        """
        Iterate over recorded effects without creating a copy.

        Memory-efficient alternative to get_all_records() for cases where
        iteration is sufficient and list mutation is not needed. The returned
        iterator yields the internal records directly, avoiding the overhead
        of copying for large recordings.

        Returns:
            Iterator[ModelEffectRecord]: Iterator over all recorded effects.

        Example:
            >>> recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
            >>> recorder.record("http.get", {"url": "..."}, {"status": 200})
            >>> for record in recorder.iter_records():
            ...     print(record.effect_type)
            http.get

        Note:
            The records themselves are immutable (frozen), so they are safe
            to use even though the iterator doesn't copy them. However, do
            not modify the internal list while iterating.

        .. versionadded:: 0.4.0
        """
        return iter(self._records)

    @property
    def record_count(self) -> int:
        """
        Return the number of recorded effects.

        Memory-efficient alternative to len(get_all_records()) that avoids
        creating a copy of the records list.

        Returns:
            int: Number of recorded effects.

        Example:
            >>> recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
            >>> recorder.record("http.get", {"url": "..."}, {"status": 200})
            >>> recorder.record_count
            1

        .. versionadded:: 0.4.0
        """
        return len(self._records)


# Verify protocol compliance at module load time
_recorder_check: ProtocolEffectRecorder = ServiceEffectRecorder()

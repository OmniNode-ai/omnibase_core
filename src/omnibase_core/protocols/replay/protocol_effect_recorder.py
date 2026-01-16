"""
ProtocolEffectRecorder - Protocol for effect recording and replay.

This protocol defines the interface for recording and replaying effects
in the ONEX pipeline, enabling deterministic execution for testing and debugging.

Design:
    Uses dependency inversion - Core defines the interface, and implementations
    provide recording (capture effects), replay (stub effects), or pass-through
    (production) behavior.

Architecture:
    Pipeline context receives an effect recorder via injection. In recording mode,
    effects are captured with their intents and results. In replay mode, the
    recorder returns pre-recorded results instead of executing real effects.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.replay import ProtocolEffectRecorder
        from omnibase_core.services.replay.service_effect_recorder import ServiceEffectRecorder
        from omnibase_core.enums.replay import EnumRecorderMode

        # Production mode - pass-through (no recording)
        recorder: ProtocolEffectRecorder = ServiceEffectRecorder()

        # Recording mode - capture effects
        recorder: ProtocolEffectRecorder = ServiceEffectRecorder(
            mode=EnumRecorderMode.RECORDING
        )
        record = recorder.record(
            effect_type="http.get",
            intent={"url": "https://api.example.com"},
            result={"status_code": 200},
        )

        # Replay mode - stub effects
        records = recorder.get_all_records()
        replay_recorder = ServiceEffectRecorder(
            mode=EnumRecorderMode.REPLAYING,
            records=records,
        )
        result = replay_recorder.get_replay_result(
            effect_type="http.get",
            intent={"url": "https://api.example.com"},
        )

Related:
    - OMN-1116: Implement Effect Recorder for Replay Infrastructure
    - ServiceEffectRecorder: Default implementation
    - ModelEffectRecord: Effect record model

.. versionadded:: 0.4.0
"""

__all__ = ["ProtocolEffectRecorder"]

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
    from omnibase_core.types.type_json import JsonType


@runtime_checkable
class ProtocolEffectRecorder(Protocol):
    """
    Protocol for recording and replaying effects.

    Defines the interface for effect recorders that capture effect intents
    and results during recording mode and return pre-recorded results during
    replay mode.

    Implementations must support three modes:
    - PASS_THROUGH: Effects execute normally (production)
    - RECORDING: Effects execute and results are captured
    - REPLAYING: Effects return pre-recorded results

    Thread Safety:
        Implementations should be thread-safe as multiple pipeline stages
        may access the recorder concurrently.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.replay import ProtocolEffectRecorder

            class MockRecorder:
                '''Test implementation that records everything.'''

                def __init__(self) -> None:
                    self._recording = True
                    self._replaying = False
                    self._records: list[ModelEffectRecord] = []

                @property
                def is_recording(self) -> bool:
                    return self._recording

                @property
                def is_replaying(self) -> bool:
                    return self._replaying

                def record(
                    self,
                    effect_type: str,
                    intent: dict[str, JsonType],
                    result: dict[str, JsonType],
                    success: bool = True,
                    error_message: str | None = None,
                ) -> ModelEffectRecord:
                    ...

                def get_replay_result(
                    self, effect_type: str, intent: dict[str, JsonType]
                ) -> dict[str, JsonType] | None:
                    ...

                def get_all_records(self) -> list[ModelEffectRecord]:
                    return list(self._records)

            # Verify protocol compliance
            recorder: ProtocolEffectRecorder = MockRecorder()
            assert isinstance(recorder, ProtocolEffectRecorder)

    .. versionadded:: 0.4.0
    """

    @property
    def is_recording(self) -> bool:
        """
        Return whether the recorder is in recording mode.

        In recording mode, effects are executed and their intents and results
        are captured for later replay.

        Returns:
            bool: True if in recording mode, False otherwise.

        Example:
            .. code-block:: python

                recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
                assert recorder.is_recording is True
        """
        ...

    @property
    def is_replaying(self) -> bool:
        """
        Return whether the recorder is in replay mode.

        In replay mode, effects return pre-recorded results instead of
        executing real effects.

        Returns:
            bool: True if in replay mode, False otherwise.

        Example:
            .. code-block:: python

                recorder = ServiceEffectRecorder(mode=EnumRecorderMode.REPLAYING, records=records)
                assert recorder.is_replaying is True
        """
        ...

    def record(
        self,
        effect_type: str,
        intent: "dict[str, JsonType]",
        result: "dict[str, JsonType]",
        success: bool = True,
        error_message: str | None = None,
    ) -> "ModelEffectRecord":
        """
        Record an effect execution.

        Captures the effect intent (what was requested) and result (what happened)
        for later replay. Only records in RECORDING mode; no-op in other modes.

        Args:
            effect_type: Type identifier for the effect (e.g., "http.get", "db.query").
            intent: What was requested (input parameters for the effect).
            result: What happened (output data from the effect execution).
            success: Whether the effect succeeded. Defaults to True.
            error_message: Error message if the effect failed. Defaults to None.

        Returns:
            ModelEffectRecord: The created effect record.

        Example:
            .. code-block:: python

                record = recorder.record(
                    effect_type="http.get",
                    intent={"url": "https://api.example.com", "method": "GET"},
                    result={"status_code": 200, "body": {"data": "value"}},
                )
                print(f"Recorded effect at sequence {record.sequence_index}")
        """
        ...

    def get_replay_result(
        self, effect_type: str, intent: "dict[str, JsonType]"
    ) -> "dict[str, JsonType] | None":
        """
        Get pre-recorded result for replay.

        Looks up a pre-recorded result that matches the given effect_type and intent.
        Only works in REPLAYING mode; returns None in other modes.

        Args:
            effect_type: Type identifier for the effect.
            intent: What was requested (must match recorded intent exactly).

        Returns:
            dict[str, JsonType] | None: The pre-recorded result if found, None otherwise.

        Example:
            .. code-block:: python

                result = recorder.get_replay_result(
                    effect_type="http.get",
                    intent={"url": "https://api.example.com", "method": "GET"},
                )
                if result is not None:
                    print(f"Replaying: status={result['status_code']}")
                else:
                    print("No recording found, executing real effect")
        """
        ...

    def get_all_records(self) -> "list[ModelEffectRecord]":
        """
        Return all recorded effects.

        Returns a copy of all effect records captured during recording.
        The returned list is safe to modify without affecting internal state.

        Returns:
            list[ModelEffectRecord]: Copy of all recorded effects.

        Example:
            .. code-block:: python

                records = recorder.get_all_records()
                print(f"Captured {len(records)} effects")
                for record in records:
                    print(f"  {record.sequence_index}: {record.effect_type}")
        """
        ...

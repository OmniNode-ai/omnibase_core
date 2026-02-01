"""
EnumRecorderMode - Recorder operating mode enum for replay infrastructure.

This module provides the EnumRecorderMode enum that determines how the
effect recorder handles recording and replay.

Design:
    Three operating modes support different execution contexts:
    - PASS_THROUGH: Production mode - no recording, effects execute normally
    - RECORDING: Capture mode - effects execute and results are recorded
    - REPLAYING: Replay mode - effects return pre-recorded results

Usage:
    .. code-block:: python

        from omnibase_core.enums.replay import EnumRecorderMode

        # Production mode (default)
        mode = EnumRecorderMode.PASS_THROUGH

        # Recording mode for capturing effects
        mode = EnumRecorderMode.RECORDING

        # Replay mode for deterministic execution
        mode = EnumRecorderMode.REPLAYING

Related:
    - OMN-1116: Implement Effect Recorder for Replay Infrastructure
    - ServiceEffectRecorder: Uses this enum for mode configuration
    - ProtocolEffectRecorder: Protocol defining recorder interface

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["EnumRecorderMode"]

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRecorderMode(StrValueHelper, str, Enum):
    """
    Recorder operating mode.

    Determines how the recorder handles effect recording and replay.

    Values:
        PASS_THROUGH: Production mode - no recording, effects execute normally.
        RECORDING: Capture mode - effects execute and results are recorded.
        REPLAYING: Replay mode - effects return pre-recorded results.

    Example:
        >>> from omnibase_core.enums.replay import EnumRecorderMode
        >>> mode = EnumRecorderMode.RECORDING
        >>> mode.value
        'recording'

    .. versionadded:: 0.4.0
    """

    PASS_THROUGH = "pass_through"
    RECORDING = "recording"
    REPLAYING = "replaying"

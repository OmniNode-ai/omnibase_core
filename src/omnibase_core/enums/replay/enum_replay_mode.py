"""Replay mode enum for deterministic replay infrastructure.

This module defines the modes of operation for the replay infrastructure,
enabling deterministic execution recording and playback.

.. versionadded:: 0.4.0
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumReplayMode(StrValueHelper, str, Enum):
    """Mode for replay infrastructure.

    Defines the operating mode for deterministic replay:

    - **PRODUCTION**: Normal execution mode. No recording or replay occurs.
      Time, RNG, and effects behave normally.

    - **RECORDING**: Execute normally while capturing all non-determinism
      (time values, RNG outputs, effect results) for later replay.

    - **REPLAYING**: Replay a previous execution deterministically using
      captured data. Time is frozen, RNG is seeded, and effects return
      recorded results.

    Thread Safety:
        Enum values are immutable and thread-safe.

    Example:
        >>> mode = EnumReplayMode.RECORDING
        >>> mode == "recording"
        True
        >>> EnumReplayMode("production")
        <EnumReplayMode.PRODUCTION: 'production'>

    .. versionadded:: 0.4.0
    """

    PRODUCTION = "production"
    """Normal execution, no recording or replay."""

    RECORDING = "recording"
    """Execute and capture non-determinism for replay."""

    REPLAYING = "replaying"
    """Replay from captured data deterministically."""


__all__ = ["EnumReplayMode"]

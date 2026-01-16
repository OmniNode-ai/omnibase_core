"""
Protocol for replay progress callbacks.

This module provides a type-safe Protocol for callbacks that receive
replay progress updates during corpus replay orchestration.

The protocol enables structural subtyping (duck typing) for callback
functions, providing stronger type safety than `Callable` while
maintaining flexibility for any callable that matches the signature.

Example:
    >>> from omnibase_core.protocols import ProtocolReplayProgressCallback
    >>> from omnibase_core.models.replay import ModelCorpusReplayProgress
    >>>
    >>> def my_callback(progress: ModelCorpusReplayProgress) -> None:
    ...     print(f"Progress: {progress.completion_percent:.1f}%")
    >>>
    >>> # Type checker knows my_callback satisfies ProtocolReplayProgressCallback

Related:
    - OMN-1204: Corpus Replay Orchestrator
    - ModelCorpusReplayProgress: Progress data passed to callback
    - ModelCorpusReplayConfig: Config that holds the callback

.. versionadded:: 0.6.0
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.replay.model_corpus_replay_progress import (
        ModelCorpusReplayProgress,
    )

__all__ = ["ProtocolReplayProgressCallback"]


@runtime_checkable
class ProtocolReplayProgressCallback(Protocol):
    """
    Protocol for replay progress callback functions.

    Defines the signature for callbacks that receive progress updates
    during corpus replay execution. Any callable matching this signature
    satisfies the protocol through structural subtyping.

    The callback is invoked:
    - Before each execution starts (with current progress)
    - After each execution completes (with updated progress)

    Thread Safety:
        Callbacks should be thread-safe if used with parallel replay
        (concurrency > 1), as they may be called from multiple async
        tasks concurrently.

    Example:
        >>> def log_progress(progress: ModelCorpusReplayProgress) -> None:
        ...     print(f"[{progress.completion_percent:.1f}%] "
        ...           f"{progress.completed}/{progress.total} complete")
        >>>
        >>> class ProgressTracker:
        ...     def __call__(self, progress: ModelCorpusReplayProgress) -> None:
        ...         self.last_progress = progress

    Note:
        The callback should not raise exceptions. If it does, the
        orchestrator will catch and log the error but continue execution.

    .. versionadded:: 0.6.0
    """

    def __call__(self, progress: "ModelCorpusReplayProgress") -> None:
        """
        Called when replay progress updates.

        Args:
            progress: Current replay progress state including counts,
                timing, and current execution information.

        Note:
            This method should complete quickly to avoid slowing down
            replay execution. For expensive operations (e.g., database
            writes), consider buffering updates or using a queue.
        """
        ...

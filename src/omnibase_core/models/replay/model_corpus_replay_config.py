"""
ModelCorpusReplayConfig - Configuration for corpus replay orchestration.

This module provides the ModelCorpusReplayConfig model for configuring
how a corpus should be replayed, including concurrency, error handling,
and subset filtering options.

Thread Safety:
    ModelCorpusReplayConfig is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelCorpusReplayConfig

        # Sequential replay with fail-fast
        config = ModelCorpusReplayConfig(
            concurrency=1,
            fail_fast=True,
        )

        # Parallel replay with continue-on-failure
        config = ModelCorpusReplayConfig(
            concurrency=4,
            fail_fast=False,
            config_overrides={"timeout_ms": 5000},
        )

Related:
    - OMN-1204: Corpus Replay Orchestrator
    - ServiceCorpusReplayOrchestrator: Service that uses this config

.. versionadded:: 0.6.0
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.replay.model_subset_filter import ModelSubsetFilter

# Import at runtime (not TYPE_CHECKING) because Pydantic's model_rebuild()
# needs to resolve this type annotation when the replay __init__.py calls it.
# The Protocol is lightweight and safe to import at runtime.
from omnibase_core.protocols.protocol_replay_progress_callback import (
    ProtocolReplayProgressCallback,
)

DEFAULT_RETRY_DELAY_MS: float = 100.0
"""Default delay between retries in milliseconds."""


class ModelCorpusReplayConfig(BaseModel):
    """
    Configuration for corpus replay orchestration.

    Controls how the corpus replay orchestrator executes replays,
    including concurrency settings, error handling behavior,
    configuration overrides, and subset filtering.

    Attributes:
        concurrency: Number of concurrent replay workers (1 = sequential).
        fail_fast: If True, stop on first failure. If False, continue.
        config_overrides: Optional dict of configuration overrides to inject.
        subset_filter: Optional filter to replay only a subset of executions.
        max_retries: Maximum retries for transient failures (0 = no retries).
        retry_delay_ms: Delay between retries in milliseconds.

    Thread Safety:
        This model is frozen (immutable) after creation, making it safe
        to share across threads. Note that progress_callback is excluded
        from serialization.

    Example:
        >>> config = ModelCorpusReplayConfig(
        ...     concurrency=4,
        ...     fail_fast=False,
        ...     config_overrides={"timeout_ms": 5000},
        ... )
        >>> config.is_sequential
        False

    .. versionadded:: 0.6.0
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    concurrency: int = Field(
        default=1,
        ge=1,
        description="Number of concurrent replay workers (1 = sequential)",
    )

    fail_fast: bool = Field(
        default=False,
        description="If True, stop on first failure. If False, continue all.",
    )

    # ONEX_EXCLUDE: dict_str_any - user-provided config overrides with arbitrary structure
    config_overrides: dict[str, Any] | None = Field(
        default=None,
        description="Optional configuration overrides to inject into each replay",
    )

    subset_filter: ModelSubsetFilter | None = Field(
        default=None,
        description="Optional filter to replay only a subset of executions",
    )

    max_retries: int = Field(
        default=0,
        ge=0,
        description="Maximum retries for transient failures (0 = no retries)",
    )

    retry_delay_ms: float = Field(
        default=DEFAULT_RETRY_DELAY_MS,
        ge=0.0,
        description="Delay between retries in milliseconds",
    )

    # Note: progress_callback is not serializable, excluded from model_dump
    # Using ProtocolReplayProgressCallback for stronger type safety (OMN-1204)
    progress_callback: ProtocolReplayProgressCallback | None = Field(
        default=None,
        exclude=True,
        description="Optional callback for progress updates",
    )

    @property
    def is_sequential(self) -> bool:
        """Check if replay should be sequential.

        Returns:
            True if concurrency is 1.
        """
        return self.concurrency == 1

    @property
    def is_parallel(self) -> bool:
        """Check if replay should be parallel.

        Returns:
            True if concurrency > 1.
        """
        return self.concurrency > 1

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        mode = "sequential" if self.is_sequential else f"parallel({self.concurrency})"
        error_mode = "fail-fast" if self.fail_fast else "continue-on-failure"
        return f"ReplayConfig({mode}, {error_mode})"


__all__ = ["ModelCorpusReplayConfig"]

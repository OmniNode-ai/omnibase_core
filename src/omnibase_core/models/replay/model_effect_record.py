"""
ModelEffectRecord - Effect record model for replay infrastructure.

This module provides the ModelEffectRecord model that captures effect intent
and result pairs for deterministic replay in the ONEX pipeline.

Design:
    Effect records store what was requested (intent) and what happened (result)
    so that effects can be stubbed during replay execution. Each record has a
    sequence index to maintain execution order.

Architecture:
    During recording mode, ServiceEffectRecorder captures each effect execution as
    a ModelEffectRecord. During replay mode, the recorder returns pre-recorded
    results instead of executing real effects.

Thread Safety:
    ModelEffectRecord is frozen (immutable) after creation, making it safe
    to share across threads.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelEffectRecord
        from datetime import datetime, timezone

        # Create a record of an HTTP effect
        record = ModelEffectRecord(
            effect_type="http.get",
            intent={
                "url": "https://api.example.com/users",
                "method": "GET",
                "headers": {"Authorization": "Bearer token"},
            },
            result={
                "status_code": 200,
                "body": [{"id": 1, "name": "Alice"}],
            },
            captured_at=datetime.now(timezone.utc),
            sequence_index=0,
        )

        # Record for a failed effect
        error_record = ModelEffectRecord(
            effect_type="db.query",
            intent={"query": "SELECT * FROM nonexistent"},
            result={},
            captured_at=datetime.now(timezone.utc),
            sequence_index=1,
            success=False,
            error_message="Table 'nonexistent' does not exist",
        )

Related:
    - OMN-1116: Implement Effect Recorder for Replay Infrastructure
    - ServiceEffectRecorder: Uses ModelEffectRecord for capture and replay
    - ProtocolEffectRecorder: Protocol defining recorder interface

.. versionadded:: 0.4.0
"""

__all__ = ["ModelEffectRecord"]

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_json import JsonType


class ModelEffectRecord(BaseModel):
    """
    Captured effect intent and result pair for replay.

    Records what was requested (intent) and what happened (result)
    so effects can be stubbed during replay execution.

    Attributes:
        record_id: Unique identifier for this record. Auto-generated UUID
            by default. Used for tracking and correlation.
        effect_type: Type identifier for the effect (e.g., "http.get",
            "db.query", "file.read"). Used to match effects during replay.
            This is a semantic type name, not a unique ID.
        intent: What was requested (input parameters). Captures the effect's
            input state for exact replay matching.
        result: What happened (output data). The actual result from the effect
            execution that will be returned during replay.
        captured_at: When the effect was captured. Used for debugging and
            audit trails.
        sequence_index: Order in execution sequence. Zero-indexed position
            in the recording, used to maintain deterministic replay order.
        success: Whether the effect succeeded. Defaults to True. Set to False
            for failed effects to capture error scenarios.
        error_message: Error message if the effect failed. Only populated when
            success is False. May also contain warnings for successful effects.

    Example:
        >>> from datetime import datetime, timezone
        >>> record = ModelEffectRecord(
        ...     effect_type="http.get",
        ...     intent={"url": "https://api.example.com"},
        ...     result={"status_code": 200},
        ...     captured_at=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        ...     sequence_index=0,
        ... )
        >>> record.effect_type
        'http.get'
        >>> record.success
        True

    Thread Safety:
        Thread-safe. Model is frozen (immutable) after creation.

    .. versionadded:: 0.4.0
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    record_id: UUID = Field(
        default_factory=uuid4,
        description="Unique record ID for tracking and correlation.",
    )
    effect_type: str = Field(
        ...,
        description="Type identifier for the effect (e.g., 'http.get', 'db.query').",
    )
    intent: dict[str, JsonType] = Field(
        ...,
        description="What was requested (input parameters for the effect).",
    )
    result: dict[str, JsonType] = Field(
        ...,
        description="What happened (output data from the effect execution).",
    )
    captured_at: datetime = Field(
        ...,
        description="When the effect was captured (UTC timestamp).",
    )
    sequence_index: int = Field(
        ...,
        description="Order in execution sequence (zero-indexed position).",
    )
    success: bool = Field(
        default=True,
        description="Whether the effect succeeded.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the effect failed, or warning if succeeded.",
    )

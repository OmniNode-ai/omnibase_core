"""Pattern Extraction Input Model.

Input model for pattern extraction operations.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumPatternKind
from omnibase_core.models.primitives import ModelSemVer
from omnibase_core.types.type_json import JsonType


def _default_schema_version() -> ModelSemVer:
    """Create default schema version 1.0.0."""
    return ModelSemVer(major=1, minor=0, patch=0)


class ModelPatternExtractionInput(BaseModel):
    """Input for pattern extraction operations.

    Specifies sessions to analyze, filtering criteria, and thresholds
    for pattern discovery. Supports both session-based queries and
    direct raw event input for replay/determinism.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Identification
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracing this extraction request",
    )

    # Data source (at least one required; both may be provided)
    session_ids: list[str] = Field(
        default_factory=list,
        description="Session IDs to analyze for patterns",
    )

    raw_events: list[JsonType] | None = Field(
        default=None,
        description="Raw events for direct extraction (replay/determinism support)",
    )

    # Filtering
    kinds: list[EnumPatternKind] | None = Field(
        default=None,
        description="Pattern kinds to extract (None = extract all kinds)",
    )

    time_window_start: datetime | None = Field(
        default=None,
        description="Start of time window for filtering events (UTC)",
    )

    time_window_end: datetime | None = Field(
        default=None,
        description="End of time window for filtering events (UTC)",
    )

    # Thresholds
    min_occurrences: int = Field(
        default=2,
        ge=1,
        description="Minimum occurrences for a pattern to be reported",
    )

    min_confidence: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for patterns (0.0 to 1.0)",
    )

    # Replay/determinism support
    source_snapshot_id: UUID | None = Field(
        default=None,
        description="Snapshot ID for deterministic replay",
    )

    # Versioning
    schema_version: ModelSemVer = Field(
        default_factory=_default_schema_version,
        description="Schema version for this input format",
    )

    @model_validator(mode="after")
    def validate_data_source(self) -> ModelPatternExtractionInput:
        """Validate that at least one data source is provided."""
        has_sessions = len(self.session_ids) > 0
        has_raw_events = self.raw_events is not None and len(self.raw_events) > 0

        if not has_sessions and not has_raw_events:
            raise ValueError(
                "At least one data source required: provide session_ids or raw_events"
            )

        return self

    @model_validator(mode="after")
    def validate_time_window(self) -> ModelPatternExtractionInput:
        """Validate time window ordering when both bounds are provided."""
        if self.time_window_start is not None and self.time_window_end is not None:
            if self.time_window_start >= self.time_window_end:
                raise ValueError(
                    "time_window_start must be strictly less than time_window_end"
                )
        return self


__all__ = ["ModelPatternExtractionInput"]

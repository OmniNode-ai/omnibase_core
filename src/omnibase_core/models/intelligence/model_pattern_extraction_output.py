"""Pattern Extraction Output Model.

Output model for pattern extraction operations.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumPatternKind
from omnibase_core.models.intelligence.model_pattern_error import ModelPatternError
from omnibase_core.models.intelligence.model_pattern_record import ModelPatternRecord
from omnibase_core.models.intelligence.model_pattern_warning import ModelPatternWarning
from omnibase_core.models.primitives import ModelSemVer


def _default_schema_version() -> ModelSemVer:
    """Create default schema version 1.0.0."""
    return ModelSemVer(major=1, minor=0, patch=0)


def _default_patterns_by_kind() -> dict[EnumPatternKind, list[ModelPatternRecord]]:
    """Create default patterns_by_kind with all kinds initialized to empty lists.

    This ensures stable shape - all kinds are always present.
    """
    return {kind: [] for kind in EnumPatternKind}


class ModelPatternExtractionOutput(BaseModel):
    """Output from pattern extraction operations.

    Contains discovered patterns organized by kind, metrics about the
    extraction process, and structured error/warning surfaces.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Status
    success: bool = Field(
        ...,
        description="Whether extraction completed successfully",
    )

    deterministic: bool = Field(
        default=False,
        description="Whether results are deterministically reproducible",
    )

    # Results by kind (stable shape - all kinds always present)
    patterns_by_kind: dict[EnumPatternKind, list[ModelPatternRecord]] = Field(
        default_factory=_default_patterns_by_kind,
        description="Patterns organized by kind (all kinds always present)",
    )

    # Metrics
    total_patterns_found: int = Field(
        ...,
        ge=0,
        description="Total number of patterns discovered",
    )

    processing_time_ms: float = Field(
        ...,
        ge=0.0,
        description="Time spent processing in milliseconds",
    )

    sessions_analyzed: int = Field(
        ...,
        ge=0,
        description="Number of sessions analyzed",
    )

    events_scanned: int = Field(
        default=0,
        ge=0,
        description="Number of events scanned during extraction",
    )

    # Error surface (structured, not exceptions)
    warnings: list[ModelPatternWarning] = Field(
        default_factory=list,
        description="Non-fatal warnings during extraction",
    )

    errors: list[ModelPatternError] = Field(
        default_factory=list,
        description="Structured errors during extraction",
    )

    # Traceability
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID from the input request",
    )

    source_snapshot_id: UUID | None = Field(
        default=None,
        description="Snapshot ID if extraction was from a snapshot",
    )

    # Versioning
    schema_version: ModelSemVer = Field(
        default_factory=_default_schema_version,
        description="Schema version for this output format",
    )

    @model_validator(mode="after")
    def validate_patterns_by_kind_completeness(self) -> ModelPatternExtractionOutput:
        """Validate that patterns_by_kind contains all EnumPatternKind keys."""
        missing_kinds = set(EnumPatternKind) - set(self.patterns_by_kind.keys())
        if missing_kinds:
            missing_names = sorted(kind.name for kind in missing_kinds)
            raise ValueError(
                f"patterns_by_kind must contain all EnumPatternKind keys. "
                f"Missing: {', '.join(missing_names)}"
            )
        return self

    @model_validator(mode="after")
    def validate_patterns_count(self) -> ModelPatternExtractionOutput:
        """Validate that total_patterns_found matches actual patterns."""
        actual_count = sum(len(patterns) for patterns in self.patterns_by_kind.values())
        if self.total_patterns_found != actual_count:
            raise ValueError(
                f"total_patterns_found ({self.total_patterns_found}) does not match "
                f"actual pattern count ({actual_count})"
            )
        return self


__all__ = ["ModelPatternExtractionOutput"]

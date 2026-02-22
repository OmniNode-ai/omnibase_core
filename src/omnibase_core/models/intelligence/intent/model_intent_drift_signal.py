# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intent drift detection output model.

Represents a detected drift signal for an in-progress intent session.
Drift occurs when observed tool usage, file surface, or scope diverges
from the originally classified intent class, indicating the session may
have shifted purpose.

Part of the Intent Intelligence Framework (OMN-2486).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.intelligence.enum_drift_type import EnumDriftType

__all__ = ["ModelIntentDriftSignal"]


class ModelIntentDriftSignal(BaseModel):
    """Drift detection output for an intent session.

    Produced when the drift detection subsystem observes that ongoing tool
    calls, file access patterns, or scope breadth no longer align with the
    originally classified intent class.

    Attributes:
        intent_id: The intent being monitored for drift.
        drift_type: Category of drift detected.
            - ``TOOL_MISMATCH``: Tools used do not match expected pattern.
            - ``FILE_SURFACE``: File access pattern diverged from intent.
            - ``SCOPE_EXPANSION``: Scope has grown beyond original intent boundary.
        description: Human-readable description of the detected drift.
        detected_at: Timestamp when drift was detected (UTC).
            Callers must inject this value — no ``datetime.now()`` defaults.
        severity: Normalized severity score in [0.0, 1.0].
            0.0 = negligible drift, 1.0 = complete divergence from original intent.

    Example:
        >>> from uuid import uuid4
        >>> from datetime import UTC, datetime
        >>> signal = ModelIntentDriftSignal(
        ...     intent_id=uuid4(),
        ...     drift_type=EnumDriftType.SCOPE_EXPANSION,
        ...     description="Session now touches 12 files vs expected 2",
        ...     detected_at=datetime.now(UTC),
        ...     severity=0.75,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    intent_id: UUID = Field(
        description="The intent being monitored for drift",
    )
    drift_type: EnumDriftType = Field(
        description=(
            "Category of drift detected: TOOL_MISMATCH | FILE_SURFACE | SCOPE_EXPANSION"
        ),
    )
    description: str = Field(
        description="Human-readable description of the detected drift",
    )
    detected_at: datetime = Field(
        description=(
            "Timestamp when drift was detected (UTC). "
            "Callers must inject this value — no datetime.now() defaults."
        ),
    )
    severity: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Normalized severity score in [0.0, 1.0]. "
            "0.0 = negligible drift, 1.0 = complete divergence."
        ),
    )

"""
Session export model for Universal Conversation Memory System.

Provides proper Pydantic model for session export operations,
replacing the ugly Dict-based SessionExportType alias with clean,
type-safe ONEX-compliant model architecture.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.memory.model_session_data import ModelSessionData


class ModelSessionExport(BaseModel):
    """
    Session export model with proper type safety and validation.

    Replaces the ugly Dict[str, Union[...]] pattern with clean
    Pydantic model following ONEX architectural standards.

    Handles export and import of session data with proper validation
    and type safety throughout the process.
    """

    sessions: dict[str, ModelSessionData] = Field(
        ...,
        description="Dictionary mapping session IDs to session data models",
    )
    current_session: str = Field(..., description="ID of the currently active session")
    exported_at: str = Field(..., description="ISO timestamp when export was created")
    export_version: str = Field(
        default="1.0",
        description="Export format version for compatibility",
    )
    total_sessions: int = Field(..., description="Total number of sessions in export")

    # Optional metadata for enhanced export tracking
    exported_by: str = Field(
        default="Universal Memory CLI",
        description="Tool that created the export",
    )
    export_format: str = Field(default="json", description="Export file format")

    class Config:
        """Pydantic configuration for ONEX compliance."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        validate_assignment = True
        extra = "forbid"  # Strict validation - no extra fields allowed

    def model_post_init(self, __context) -> None:
        """Post-initialization validation."""
        # Ensure current_session exists in sessions
        if self.current_session not in self.sessions:
            msg = f"Current session '{self.current_session}' not found in sessions"
            raise ValueError(
                msg,
            )

        # Validate total_sessions matches actual count
        if self.total_sessions != len(self.sessions):
            msg = f"Total sessions mismatch: expected {self.total_sessions}, got {len(self.sessions)}"
            raise ValueError(
                msg,
            )

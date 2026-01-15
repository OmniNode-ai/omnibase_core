"""
Node Timestamps Model.

Timing and lifecycle information for nodes.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelNodeTimestamps(BaseModel):
    """
    Node timing and lifecycle information.

    Focused on creation, modification, and validation timestamps.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Timestamps
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Update timestamp")
    last_validated: datetime | None = Field(
        default=None,
        description="Last validation timestamp",
    )

    @property
    def has_creation_time(self) -> bool:
        """Check if creation time is available."""
        return self.created_at is not None

    @property
    def has_update_time(self) -> bool:
        """Check if update time is available."""
        return self.updated_at is not None

    @property
    def has_validation_time(self) -> bool:
        """Check if validation time is available."""
        return self.last_validated is not None

    @property
    def age_days(self) -> float | None:
        """Get age in days since creation."""
        if not self.created_at:
            return None
        return (datetime.now(UTC) - self.created_at).total_seconds() / 86400

    @property
    def last_modified_days_ago(self) -> float | None:
        """Get days since last modification."""
        if not self.updated_at:
            return None
        return (datetime.now(UTC) - self.updated_at).total_seconds() / 86400

    @property
    def validation_age_days(self) -> float | None:
        """Get days since last validation."""
        if not self.last_validated:
            return None
        return (datetime.now(UTC) - self.last_validated).total_seconds() / 86400

    def is_recently_created(self, days: int = 7) -> bool:
        """Check if node was created recently."""
        age = self.age_days
        return age is not None and age <= days

    def is_recently_updated(self, days: int = 30) -> bool:
        """Check if node was updated recently."""
        last_modified = self.last_modified_days_ago
        return last_modified is not None and last_modified <= days

    def needs_validation(self, days: int = 90) -> bool:
        """Check if node needs validation."""
        if not self.last_validated:
            return True
        validation_age = self.validation_age_days
        return validation_age is not None and validation_age > days

    def is_stale(self, days: int = 180) -> bool:
        """Check if node is stale (not updated in specified days)."""
        last_modified = self.last_modified_days_ago
        return last_modified is not None and last_modified > days

    def update_created_timestamp(self, timestamp: datetime | None = None) -> None:
        """Update created timestamp."""
        self.created_at = timestamp or datetime.now(UTC)

    def update_modified_timestamp(self, timestamp: datetime | None = None) -> None:
        """Update modified timestamp."""
        self.updated_at = timestamp or datetime.now(UTC)

    def update_validation_timestamp(self, timestamp: datetime | None = None) -> None:
        """Update validation timestamp."""
        self.last_validated = timestamp or datetime.now(UTC)

    def touch_all_timestamps(self) -> None:
        """Update all timestamps to current time."""
        now = datetime.now(UTC)
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        self.last_validated = now

    def get_lifecycle_summary(self) -> dict[str, str | None]:
        """Get lifecycle summary."""
        return {
            "created": self.created_at.isoformat() if self.created_at else None,
            "updated": self.updated_at.isoformat() if self.updated_at else None,
            "validated": (
                self.last_validated.isoformat() if self.last_validated else None
            ),
            "age_days": f"{self.age_days:.1f}" if self.age_days else None,
            "last_modified_days_ago": (
                f"{self.last_modified_days_ago:.1f}"
                if self.last_modified_days_ago
                else None
            ),
            "validation_age_days": (
                f"{self.validation_age_days:.1f}" if self.validation_age_days else None
            ),
        }

    def get_staleness_level(self) -> str:
        """Get descriptive staleness level."""
        last_modified = self.last_modified_days_ago
        if last_modified is None:
            return "Unknown"
        if last_modified <= 7:
            return "Fresh"
        if last_modified <= 30:
            return "Recent"
        if last_modified <= 90:
            return "Aging"
        if last_modified <= 180:
            return "Stale"
        return "Very Stale"

    @classmethod
    def create_new(cls) -> ModelNodeTimestamps:
        """Create timestamps for a new node."""
        now = datetime.now(UTC)
        return cls(
            created_at=now,
            updated_at=now,
            last_validated=now,
        )

    @classmethod
    def create_with_creation_time(cls, created_at: datetime) -> ModelNodeTimestamps:
        """Create timestamps with specific creation time."""
        return cls(
            created_at=created_at,
            updated_at=created_at,
            last_validated=None,
        )

    @classmethod
    def create_unvalidated(cls) -> ModelNodeTimestamps:
        """Create timestamps for node that needs validation."""
        now = datetime.now(UTC)
        return cls(
            created_at=now,
            updated_at=now,
            last_validated=None,  # intentionally None
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Pack timestamp fields into metadata dict
        result["metadata"] = {
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
            "last_validated": (
                self.last_validated.isoformat() if self.last_validated else None
            ),
            "age_days": self.age_days,
            "last_modified_days_ago": self.last_modified_days_ago,
            "validation_age_days": self.validation_age_days,
            "staleness_level": self.get_staleness_level(),
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If metadata setting logic fails
        """
        for key, value in metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = ["ModelNodeTimestamps"]

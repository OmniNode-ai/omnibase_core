"""
Discriminated union model for migration conflicts.

Replaces Union[TypedDictMigrationDuplicateConflictDict, TypedDictMigrationNameConflictDict]
with ONEX-compliant discriminated union pattern.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_migration_conflict_type import EnumMigrationConflictType

from .migration_types import (
    TypedDictMigrationDuplicateConflictDict,
    TypedDictMigrationNameConflictDict,
)


class ModelMigrationConflictUnion(BaseModel):
    """
    Discriminated union for migration conflicts to replace Union patterns.

    Handles both name conflicts and exact duplicate conflicts with proper
    type discrimination using a conflict_type field.

    Replaces: Union[TypedDictMigrationDuplicateConflictDict, TypedDictMigrationNameConflictDict]
    """

    conflict_type: EnumMigrationConflictType = Field(
        description="Type discriminator for conflict union",
    )

    # Common fields present in both conflict types
    protocol_name: str = Field(description="Name of the conflicting protocol")
    source_file: str = Field(description="Path to source protocol file")
    spi_file: str = Field(description="Path to SPI protocol file")
    recommendation: str = Field(description="Recommended resolution action")

    # Fields specific to name conflicts
    source_signature: str | None = Field(
        default=None,
        description="Source protocol signature hash (name conflicts only)",
    )
    spi_signature: str | None = Field(
        default=None,
        description="SPI protocol signature hash (name conflicts only)",
    )

    # Fields specific to duplicate conflicts
    signature_hash: str | None = Field(
        default=None,
        description="Common signature hash (duplicate conflicts only)",
    )

    @field_validator("source_signature", "spi_signature")
    @classmethod
    def validate_name_conflict_fields(
        cls,
        v: str | None,
        info: ValidationInfo,
    ) -> str | None:
        """Ensure name conflict fields are present when conflict_type is name_conflict."""
        conflict_type = info.data.get("conflict_type")
        if conflict_type == EnumMigrationConflictType.NAME_CONFLICT and v is None:
            raise ValueError(
                "source_signature and spi_signature required for name conflicts",
            )
        return v

    @field_validator("signature_hash")
    @classmethod
    def validate_duplicate_conflict_fields(
        cls,
        v: str | None,
        info: ValidationInfo,
    ) -> str | None:
        """Ensure duplicate conflict fields are present when conflict_type is exact_duplicate."""
        conflict_type = info.data.get("conflict_type")
        if conflict_type == EnumMigrationConflictType.EXACT_DUPLICATE and v is None:
            raise ValueError("signature_hash required for exact duplicate conflicts")
        return v

    @classmethod
    def from_name_conflict(
        cls,
        conflict_dict: TypedDictMigrationNameConflictDict,
    ) -> ModelMigrationConflictUnion:
        """Create union instance from name conflict TypedDict."""
        return cls(
            conflict_type=EnumMigrationConflictType.NAME_CONFLICT,
            protocol_name=conflict_dict["protocol_name"],
            source_file=conflict_dict["source_file"],
            spi_file=conflict_dict["spi_file"],
            recommendation=conflict_dict["recommendation"],
            source_signature=conflict_dict["source_signature"],
            spi_signature=conflict_dict["spi_signature"],
        )

    @classmethod
    def from_duplicate_conflict(
        cls,
        conflict_dict: TypedDictMigrationDuplicateConflictDict,
    ) -> ModelMigrationConflictUnion:
        """Create union instance from duplicate conflict TypedDict."""
        return cls(
            conflict_type=EnumMigrationConflictType.EXACT_DUPLICATE,
            protocol_name=conflict_dict["protocol_name"],
            source_file=conflict_dict["source_file"],
            spi_file=conflict_dict["spi_file"],
            recommendation=conflict_dict["recommendation"],
            signature_hash=conflict_dict["signature_hash"],
        )

    def to_name_conflict_dict(self) -> TypedDictMigrationNameConflictDict:
        """Convert to name conflict TypedDict format."""
        if self.conflict_type != EnumMigrationConflictType.NAME_CONFLICT:
            raise ValueError("Cannot convert to name conflict: wrong conflict type")

        if self.source_signature is None or self.spi_signature is None:
            raise ValueError("Missing required fields for name conflict conversion")

        return TypedDictMigrationNameConflictDict(
            type=self.conflict_type,
            protocol_name=self.protocol_name,
            source_file=self.source_file,
            spi_file=self.spi_file,
            recommendation=self.recommendation,
            source_signature=self.source_signature,
            spi_signature=self.spi_signature,
        )

    def to_duplicate_conflict_dict(self) -> TypedDictMigrationDuplicateConflictDict:
        """Convert to duplicate conflict TypedDict format."""
        if self.conflict_type != EnumMigrationConflictType.EXACT_DUPLICATE:
            raise ValueError(
                "Cannot convert to duplicate conflict: wrong conflict type",
            )

        if self.signature_hash is None:
            raise ValueError(
                "Missing required fields for duplicate conflict conversion",
            )

        return TypedDictMigrationDuplicateConflictDict(
            type=self.conflict_type,
            protocol_name=self.protocol_name,
            source_file=self.source_file,
            spi_file=self.spi_file,
            recommendation=self.recommendation,
            signature_hash=self.signature_hash,
        )

    def is_name_conflict(self) -> bool:
        """Check if this is a name conflict."""
        return self.conflict_type == EnumMigrationConflictType.NAME_CONFLICT

    def is_duplicate_conflict(self) -> bool:
        """Check if this is an exact duplicate conflict."""
        return self.conflict_type == EnumMigrationConflictType.EXACT_DUPLICATE

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for ONEX compliance
__all__ = ["ModelMigrationConflictUnion"]

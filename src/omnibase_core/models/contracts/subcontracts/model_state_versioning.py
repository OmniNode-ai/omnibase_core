"""
State Versioning Model - ONEX Standards Compliant.

Individual model for state versioning configuration.
Part of the State Management Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_state_management import EnumVersionScheme


class ModelStateVersioning(BaseModel):
    """
    State versioning and migration configuration.

    Defines versioning policies, migration strategies,
    and state transition handling.
    """

    versioning_enabled: bool = Field(
        default=True,
        description="Enable state versioning",
    )

    version_scheme: EnumVersionScheme = Field(
        default=EnumVersionScheme.SEMANTIC,
        description="Versioning scheme for state",
    )

    migration_enabled: bool = Field(default=True, description="Enable state migration")

    migration_strategies: list[str] = Field(
        default_factory=list,
        description="Available migration strategies",
    )

    forward_compatibility: bool = Field(
        default=True,
        description="Maintain forward state compatibility",
    )

    version_retention: int = Field(
        default=5,
        description="Number of state versions to retain",
        ge=1,
    )

    rollback_enabled: bool = Field(
        default=True,
        description="Enable state rollback to previous versions",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

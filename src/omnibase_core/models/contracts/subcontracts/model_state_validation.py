"""
State Validation Model.

Individual model for state validation configuration.
Part of the State Management Subcontract Model family.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelStateValidation(BaseModel):
    """
    State validation configuration.

    Defines validation rules, integrity checks,
    and consistency verification for state data.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    validation_enabled: bool = Field(
        default=True,
        description="Enable state validation",
    )

    schema_validation: bool = Field(
        default=True,
        description="Enable schema validation for state",
    )

    integrity_checks: bool = Field(default=True, description="Enable integrity checks")

    consistency_checks: bool = Field(
        default=False,
        description="Enable consistency validation",
    )

    validation_rules: list[str] = Field(
        default_factory=list,
        description="Custom validation rules",
    )

    repair_enabled: bool = Field(
        default=False,
        description="Enable automatic state repair",
    )

    repair_strategies: list[str] = Field(
        default_factory=list,
        description="Available repair strategies",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

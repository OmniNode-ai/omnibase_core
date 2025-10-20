from typing import Any

from pydantic import Field

"""
State Validation Model - ONEX Standards Compliant.

Individual model for state validation configuration.
Part of the State Management Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel


class ModelStateValidation(BaseModel):
    """
    State validation configuration.

    Defines validation rules, integrity checks,
    and consistency verification for state data.
    """

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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

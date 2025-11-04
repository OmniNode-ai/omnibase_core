from pydantic import Field, field_validator

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
ModelTrustLevel: Trust level configuration for signature chains.

This model represents trust level configuration and validation.
"""

from pydantic import BaseModel


class ModelTrustLevel(BaseModel):
    """Trust level configuration for signature chains."""

    level: str = Field(
        default="standard",
        description="Trust level: high_trust, trusted, standard, partial_trust, untrusted, compromised",
        pattern=r"^(high_trust|trusted|standard|partial_trust|untrusted|compromised)$",
    )

    minimum_trusted_signatures: int = Field(
        default=0,
        description="Minimum number of signatures from trusted nodes required",
        ge=0,
    )

    require_all_trusted: bool = Field(
        default=False,
        description="Whether all signatures must be from trusted nodes",
    )

    allow_untrusted_with_majority: bool = Field(
        default=True,
        description="Allow untrusted signatures if majority are trusted",
    )

    trusted_percentage_threshold: float = Field(
        default=0.5,
        description="Minimum percentage of signatures that must be trusted",
        ge=0.0,
        le=1.0,
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate trust level value."""
        valid_levels = {
            "high_trust",
            "trusted",
            "standard",
            "partial_trust",
            "untrusted",
            "compromised",
        }
        if v not in valid_levels:
            msg = f"Invalid trust level: {v}. Must be one of: {valid_levels}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    def is_higher_than(self, other: "ModelTrustLevel") -> bool:
        """Check if this trust level is higher than another."""
        level_order = {
            "compromised": 0,
            "untrusted": 1,
            "partial_trust": 2,
            "standard": 3,
            "trusted": 4,
            "high_trust": 5,
        }
        return level_order.get(self.level, 0) > level_order.get(other.level, 0)

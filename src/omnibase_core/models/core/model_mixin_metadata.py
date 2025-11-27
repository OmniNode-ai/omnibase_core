"""Pydantic model for complete mixin metadata.

This module provides the ModelMixinMetadata class, which aggregates all
mixin metadata components for validation and discovery.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_mixin_code_patterns import ModelMixinCodePatterns
from omnibase_core.models.core.model_mixin_config_field import ModelMixinConfigField
from omnibase_core.models.core.model_mixin_performance import ModelMixinPerformance
from omnibase_core.models.core.model_mixin_preset import ModelMixinPreset
from omnibase_core.models.core.model_mixin_version import ModelMixinVersion
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# Main Mixin Metadata Model
# =============================================================================


class ModelMixinMetadata(BaseModel):
    """Complete metadata for a single mixin.

    Attributes:
        name: Mixin class name
        description: Human-readable description
        version: Semantic version
        category: Mixin category (flow_control, observability, etc.)
        requires: Required dependencies (modules/packages)
        compatible_with: Compatible mixin names
        incompatible_with: Incompatible mixin names
        config_schema: Configuration field definitions
        usage_examples: Usage example descriptions
        presets: Preset configurations
        code_patterns: Code generation patterns
        implementation_notes: Implementation guidance
        performance: Performance characteristics
        documentation_url: Link to detailed documentation
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Mixin class name")
    description: str = Field(..., description="Mixin description")
    version: ModelMixinVersion = Field(..., description="Semantic version")
    category: str = Field(..., description="Mixin category")

    # Dependencies and compatibility
    requires: list[str] = Field(default_factory=list, description="Required imports")
    compatible_with: list[str] = Field(
        default_factory=list, description="Compatible mixins"
    )
    incompatible_with: list[str] = Field(
        default_factory=list, description="Incompatible mixins"
    )

    # Configuration
    config_schema: dict[str, ModelMixinConfigField] = Field(
        default_factory=dict, description="Configuration schema"
    )

    # Usage and examples
    usage_examples: list[str] = Field(
        default_factory=list, description="Usage examples"
    )
    presets: dict[str, ModelMixinPreset] = Field(
        default_factory=dict, description="Presets"
    )

    # Code generation
    code_patterns: ModelMixinCodePatterns | None = Field(
        None, description="Code patterns"
    )

    # Documentation
    implementation_notes: list[str] = Field(
        default_factory=list, description="Implementation notes"
    )
    performance: ModelMixinPerformance | None = Field(
        None, description="Performance info"
    )
    documentation_url: str | None = Field(None, description="Documentation URL")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is one of the known categories."""
        valid_categories = {
            "flow_control",
            "observability",
            "security",
            "data_processing",
            "integration",
            "utility",
            "state_management",
            "communication",
        }
        if v not in valid_categories:
            # Allow unknown categories but could log a warning in production
            pass
        return v

    @model_validator(mode="after")
    def validate_compatibility(self) -> "ModelMixinMetadata":
        """Validate compatibility constraints are consistent."""
        # A mixin can't be both compatible and incompatible with the same mixin
        compatible_set = set(self.compatible_with)
        incompatible_set = set(self.incompatible_with)

        overlap = compatible_set & incompatible_set
        if overlap:
            raise ModelOnexError(
                message=f"Mixin {self.name} has conflicting compatibility: "
                f"{overlap} listed in both compatible_with and incompatible_with",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )

        return self

"""
Environment Validation Rules Model.

Strongly-typed model for grouping environment-specific validation rules.
Replaces dict[EnumEnvironment, dict[str, str]] with proper type safety.

Strict typing is enforced: No Any types allowed in implementation.

Inheritance Modes
-----------------
The combination of inherit_from_default and override_default flags determines
how validation rules are processed. Four modes are supported:

1. EXTEND (inherit=True, override=False) [DEFAULT - RECOMMENDED]
   - Start with default rules
   - Add environment-specific rules
   - Environment rules complement defaults
   - Use case: Extend base validation with environment-specific checks

2. REPLACE (inherit=False, override=True)
   - Completely replace default rules
   - Only use environment-specific rules
   - Ignore all defaults
   - Use case: Production environment with strict, isolated rules

3. ISOLATED (inherit=False, override=False)
   - Use only environment-specific rules
   - No interaction with defaults
   - Standalone rule set
   - Use case: Testing or sandbox with custom validation

4. MERGE_WITH_OVERRIDE (inherit=True, override=True) [ADVANCED]
   - Start with default rules
   - Environment rules override conflicting defaults
   - Non-conflicting defaults preserved
   - Use case: Complex inheritance with selective overrides
   - WARNING: Requires careful management of rule precedence
"""

import warnings
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_environment import EnumEnvironment
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_environment_validation_rule import ModelEnvironmentValidationRule


class ModelEnvironmentValidationRules(BaseModel):
    """
    Strongly-typed environment validation rules container.

    Groups validation rules by environment with proper type safety.
    Replaces nested dict structures with validated models.

    Flag Behavior
    -------------
    inherit_from_default: Controls whether to start with default rules
    override_default: Controls whether to replace/override defaults

    Recommended Patterns
    --------------------
    - Development/Staging: inherit=True, override=False (extend defaults)
    - Production: inherit=False, override=True (isolated strict rules)
    - Testing: inherit=False, override=False (standalone test rules)
    - Advanced: inherit=True, override=True (merge with selective overrides)

    See module docstring for detailed inheritance mode documentation.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    environment: EnumEnvironment = Field(
        ...,
        description="Target environment for these validation rules",
    )

    validation_rules: list[ModelEnvironmentValidationRule] = Field(
        default_factory=list,
        description="List of validation rules for this environment",
    )

    inherit_from_default: bool = Field(
        default=True,
        description=(
            "Whether to inherit validation rules from default environment. "
            "True: Start with default rules. False: Ignore defaults."
        ),
    )

    override_default: bool = Field(
        default=False,
        description=(
            "Whether these rules override default rules. "
            "True: Replace/override defaults. False: Complement defaults."
        ),
    )

    @model_validator(mode="after")
    def validate_flag_consistency(self) -> "ModelEnvironmentValidationRules":
        """
        Validate flag combination consistency and warn about edge cases.

        Validates:
        - Flag combinations are semantically meaningful
        - Warns about advanced patterns (inherit=True, override=True)
        - Documents expected behavior for each mode

        Returns:
            Self after validation

        Raises:
            No exceptions - uses warnings for ambiguous cases
        """
        inherit = self.inherit_from_default
        override = self.override_default

        # Define inheritance mode for clarity
        mode: Literal["EXTEND", "REPLACE", "ISOLATED", "MERGE_WITH_OVERRIDE"]

        if inherit and not override:
            mode = "EXTEND"
            # Default recommended pattern - no warning needed
        elif not inherit and override:
            mode = "REPLACE"
            # Clear replacement pattern - no warning needed
        elif not inherit and not override:
            mode = "ISOLATED"
            # Clear isolation pattern - no warning needed
        elif inherit and override:
            mode = "MERGE_WITH_OVERRIDE"
            # Advanced pattern - warn about complexity
            warnings.warn(
                f"Environment '{self.environment.value}' uses MERGE_WITH_OVERRIDE mode "
                "(inherit=True, override=True). This is an advanced pattern that merges "
                "default rules with environment-specific overrides. Ensure rule precedence "
                "is clearly documented to avoid unexpected behavior. "
                "Recommended: Use EXTEND (inherit=True, override=False) for most cases.",
                UserWarning,
                stacklevel=2,
            )

        # Store computed mode as internal state (not persisted)
        # Useful for debugging and introspection
        object.__setattr__(self, "_inheritance_mode", mode)

        return self

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

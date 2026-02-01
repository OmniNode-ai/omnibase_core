"""
Validation Schema Rule Model.

Strongly-typed model for configuration validation schema rules.
Replaces dict[str, str] with proper type safety.

Strict typing is enforced: No Any types allowed in implementation.
"""

import json
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_validation_rule_type import EnumValidationRuleType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelValidationSchemaRule(BaseModel):
    """
    Strongly-typed validation schema rule.

    Defines validation rules for configuration keys with type safety
    and runtime validation.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    key_name: str = Field(
        ...,
        description="Configuration key name to validate",
        min_length=1,
    )

    validation_rule: str = Field(
        ...,
        description="Validation rule expression or JSON schema fragment",
        min_length=1,
    )

    rule_type: EnumValidationRuleType = Field(
        default=EnumValidationRuleType.REGEX,
        description="Type of validation rule (regex, json_schema, range, enum)",
    )

    error_message: str | None = Field(
        default=None,
        description="Custom error message for validation failures",
    )

    is_required: bool = Field(
        default=False,
        description="Whether this validation must pass",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    @model_validator(mode="after")
    def validate_rule_format(self) -> "ModelValidationSchemaRule":
        """
        Validate that validation_rule format matches rule_type.

        Ensures:
        - REGEX rules contain valid regular expressions
        - JSON_SCHEMA rules contain valid JSON schema fragments
        - RANGE rules contain valid range expressions
        - ENUM rules contain valid enum value lists

        Raises:
            ModelOnexError: If validation_rule format doesn't match rule_type

        Returns:
            Self for method chaining
        """
        rule_type = self.rule_type
        validation_rule = self.validation_rule

        if rule_type == EnumValidationRuleType.REGEX:
            self._validate_regex_rule(validation_rule)
        elif rule_type == EnumValidationRuleType.JSON_SCHEMA:
            self._validate_json_schema_rule(validation_rule)
        elif rule_type == EnumValidationRuleType.RANGE:
            self._validate_range_rule(validation_rule)
        elif rule_type == EnumValidationRuleType.ENUM:
            self._validate_enum_rule(validation_rule)

        return self

    def _validate_regex_rule(self, rule: str) -> None:
        """
        Validate that rule is a valid regular expression.

        Args:
            rule: The regex pattern to validate

        Raises:
            ModelOnexError: If regex pattern is invalid
        """
        try:
            re.compile(rule)
        except re.error as e:
            raise ModelOnexError(
                message=(
                    f"Invalid regex pattern for rule_type=REGEX: {rule}. "
                    f"Regex compilation error: {e}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def _validate_json_schema_rule(self, rule: str) -> None:
        """
        Validate that rule is valid JSON that could be a schema fragment.

        Args:
            rule: The JSON schema fragment to validate

        Raises:
            ModelOnexError: If JSON is malformed
        """
        try:
            parsed = json.loads(rule)
            # Ensure it's a dict (valid JSON schema fragment)
            if not isinstance(parsed, dict):
                raise ModelOnexError(
                    message=(
                        f"Invalid JSON schema for rule_type=JSON_SCHEMA: {rule}. "
                        "JSON schema must be an object (dict), not a primitive type."
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
        except json.JSONDecodeError as e:
            raise ModelOnexError(
                message=(
                    f"Invalid JSON schema for rule_type=JSON_SCHEMA: {rule}. "
                    f"JSON parsing error: {e}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def _validate_range_rule(self, rule: str) -> None:
        """
        Validate that rule is a valid range expression.

        Expected formats:
        - "min..max" (e.g., "1..10")
        - "min.." (e.g., "1..")
        - "..max" (e.g., "..10")

        Args:
            rule: The range expression to validate

        Raises:
            ModelOnexError: If range format is invalid
        """
        # Basic range validation - must contain ".."
        if ".." not in rule:
            raise ModelOnexError(
                message=(
                    f"Invalid range format for rule_type=RANGE: {rule}. "
                    "Range must contain '..' separator (e.g., '1..10', '1..', or '..10')."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        parts = rule.split("..", 1)
        if len(parts) != 2:
            raise ModelOnexError(
                message=(
                    f"Invalid range format for rule_type=RANGE: {rule}. "
                    "Range must have exactly one '..' separator."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        min_val, max_val = parts

        # Validate that non-empty parts are numeric
        if min_val and not self._is_numeric(min_val):
            raise ModelOnexError(
                message=(
                    f"Invalid range format for rule_type=RANGE: {rule}. "
                    f"Minimum value '{min_val}' is not numeric."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if max_val and not self._is_numeric(max_val):
            raise ModelOnexError(
                message=(
                    f"Invalid range format for rule_type=RANGE: {rule}. "
                    f"Maximum value '{max_val}' is not numeric."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # At least one bound must be specified
        if not min_val and not max_val:
            raise ModelOnexError(
                message=(
                    f"Invalid range format for rule_type=RANGE: {rule}. "
                    "At least one bound (min or max) must be specified."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

    def _validate_enum_rule(self, rule: str) -> None:
        """
        Validate that rule is a valid enum value list.

        Expected format: Comma-separated values (e.g., "value1,value2,value3")

        Args:
            rule: The enum values list to validate

        Raises:
            ModelOnexError: If enum format is invalid
        """
        # Split by comma and strip whitespace
        values = [v.strip() for v in rule.split(",")]

        # Must have at least one value
        if not values or all(not v for v in values):
            raise ModelOnexError(
                message=(
                    f"Invalid enum format for rule_type=ENUM: {rule}. "
                    "Enum must contain at least one non-empty value."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Check for duplicate values
        unique_values = set(values)
        if len(unique_values) != len(values):
            duplicates = [v for v in values if values.count(v) > 1]
            raise ModelOnexError(
                message=(
                    f"Invalid enum format for rule_type=ENUM: {rule}. "
                    f"Duplicate values found: {set(duplicates)}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

    @staticmethod
    def _is_numeric(value: str) -> bool:
        """
        Check if string represents a numeric value.

        Args:
            value: String to check

        Returns:
            True if value is numeric (int or float)
        """
        try:
            float(value)
            return True
        except ValueError:
            return False

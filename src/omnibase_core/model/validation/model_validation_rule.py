"""
Validation Rule Model

Structured model for validation rules that replaces List[str] usage.
"""

from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class EnumValidationRuleType(str, Enum):
    """Types of validation rules."""

    schema = "schema"
    business = "business"
    security = "security"
    performance = "performance"
    compliance = "compliance"
    formatting = "formatting"
    custom = "custom"


class EnumValidationSeverity(str, Enum):
    """Severity levels for validation rules."""

    error = "error"
    warning = "warning"
    info = "info"
    critical = "critical"


class ModelValidationRuleParameters(BaseModel):
    """
    Strongly-typed validation rule parameters.

    Replaces Dict[str, Any] with proper typing for all parameter types.
    """

    # Numeric parameters
    min_value: Optional[Union[int, float]] = Field(
        None, description="Minimum allowed value"
    )
    max_value: Optional[Union[int, float]] = Field(
        None, description="Maximum allowed value"
    )
    min_length: Optional[int] = Field(None, description="Minimum string/array length")
    max_length: Optional[int] = Field(None, description="Maximum string/array length")

    # String parameters
    allowed_values: Optional[List[str]] = Field(
        None, description="List of allowed string values"
    )
    forbidden_values: Optional[List[str]] = Field(
        None, description="List of forbidden string values"
    )
    case_sensitive: Optional[bool] = Field(
        None, description="Whether string comparisons are case sensitive"
    )

    # Pattern parameters
    regex_pattern: Optional[str] = Field(
        None, description="Regular expression pattern to match"
    )
    regex_flags: Optional[List[str]] = Field(
        None, description="Regex flags like 'i', 'm', 's'"
    )

    # File/Path parameters
    file_extensions: Optional[List[str]] = Field(
        None, description="Allowed file extensions"
    )
    path_must_exist: Optional[bool] = Field(
        None, description="Whether the path must exist"
    )
    require_absolute_path: Optional[bool] = Field(
        None, description="Whether path must be absolute"
    )

    # Schema parameters
    schema_version: Optional[str] = Field(None, description="Required schema version")
    required_fields: Optional[List[str]] = Field(
        None, description="Required field names"
    )
    forbidden_fields: Optional[List[str]] = Field(
        None, description="Forbidden field names"
    )

    # Performance parameters
    max_execution_time_ms: Optional[int] = Field(
        None, description="Maximum execution time in milliseconds"
    )
    max_memory_mb: Optional[int] = Field(None, description="Maximum memory usage in MB")

    # Custom parameters for extensibility (strongly typed)
    custom_string_params: Optional[Dict[str, str]] = Field(
        None, description="Custom string parameters"
    )
    custom_int_params: Optional[Dict[str, int]] = Field(
        None, description="Custom integer parameters"
    )
    custom_bool_params: Optional[Dict[str, bool]] = Field(
        None, description="Custom boolean parameters"
    )


class ModelValidationRule(BaseModel):
    """
    Structured validation rule model.

    Replaces string-based validation rules with proper typing
    and metadata for better validation control.
    """

    rule_name: str = Field(..., description="Unique name for the validation rule")
    rule_type: EnumValidationRuleType = Field(
        ..., description="Type of validation rule"
    )
    severity: EnumValidationSeverity = Field(
        default=EnumValidationSeverity.error, description="Severity level"
    )
    description: str = Field(
        ..., description="Human-readable description of what this rule validates"
    )

    # Rule configuration
    enabled: bool = Field(default=True, description="Whether this rule is enabled")
    pattern: Optional[str] = Field(
        None, description="Regex pattern for pattern-based rules"
    )
    expected_value: Optional[Union[str, int, float, bool]] = Field(
        None, description="Expected value for comparison rules"
    )
    parameters: Optional[ModelValidationRuleParameters] = Field(
        None, description="Strongly-typed rule parameters"
    )

    # Metadata
    tags: List[str] = Field(
        default_factory=list, description="Tags for categorizing rules"
    )
    documentation_url: Optional[str] = Field(
        None, description="URL to rule documentation"
    )
    auto_fixable: bool = Field(
        default=False, description="Whether violations can be auto-fixed"
    )

    @classmethod
    def create_schema_rule(
        cls, rule_name: str, description: str, **kwargs
    ) -> "ModelValidationRule":
        """Factory method for schema validation rules."""
        return cls(
            rule_name=rule_name,
            rule_type=EnumValidationRuleType.schema,
            description=description,
            **kwargs,
        )

    @classmethod
    def create_compliance_rule(
        cls, rule_name: str, description: str, **kwargs
    ) -> "ModelValidationRule":
        """Factory method for compliance validation rules."""
        return cls(
            rule_name=rule_name,
            rule_type=EnumValidationRuleType.compliance,
            description=description,
            **kwargs,
        )

    @classmethod
    def create_pattern_rule(
        cls,
        rule_name: str,
        description: str,
        regex_pattern: str,
        case_sensitive: bool = True,
        **kwargs,
    ) -> "ModelValidationRule":
        """Factory method for pattern-based validation rules."""
        parameters = ModelValidationRuleParameters(
            regex_pattern=regex_pattern,
            case_sensitive=case_sensitive,
            **{
                k: v
                for k, v in kwargs.items()
                if k in ModelValidationRuleParameters.model_fields
            },
        )
        return cls(
            rule_name=rule_name,
            rule_type=EnumValidationRuleType.formatting,
            description=description,
            parameters=parameters,
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ModelValidationRuleParameters.model_fields
            },
        )

    @classmethod
    def create_range_rule(
        cls,
        rule_name: str,
        description: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        **kwargs,
    ) -> "ModelValidationRule":
        """Factory method for numeric range validation rules."""
        parameters = ModelValidationRuleParameters(
            min_value=min_value,
            max_value=max_value,
            **{
                k: v
                for k, v in kwargs.items()
                if k in ModelValidationRuleParameters.model_fields
            },
        )
        return cls(
            rule_name=rule_name,
            rule_type=EnumValidationRuleType.business,
            description=description,
            parameters=parameters,
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ModelValidationRuleParameters.model_fields
            },
        )

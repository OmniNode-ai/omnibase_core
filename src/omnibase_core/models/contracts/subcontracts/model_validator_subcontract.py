"""
Validator Subcontract Model.

Schema version: v1.0.0

Dedicated subcontract model for file-based validator functionality providing:
- File targeting via glob patterns (include/exclude)
- Configurable validation rules with severity levels
- Suppression comment patterns for inline overrides
- Behavior configuration (fail-fast, parallel execution)
- Violation limit and error handling settings

This model is composed into validator node contracts that require file-based
validation functionality, providing clean separation between node logic and
validator configuration.

Distinct from ModelValidationSubcontract which handles Pydantic validation
behavior. This subcontract is specifically for file-based validators like
naming convention checkers, any_type validators, etc.

Instances are immutable after creation (frozen=True), enabling safe sharing
across threads without synchronization.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelValidatorSubcontract(BaseModel):
    """
    Validator subcontract model for file-based validation functionality.

    Comprehensive subcontract providing file targeting, validation rules,
    suppression patterns, and behavior configuration. Designed for composition
    into validator node contracts requiring file-based validation functionality.

    This is distinct from ModelValidationSubcontract which handles Pydantic
    validation behavior. This subcontract is specifically for file-based
    validators like naming convention checkers, any_type validators, etc.

    Schema Version:
        v1.0.0 - Initial version for file-based validator configuration.

    Immutability and Thread Safety:
        This model uses frozen=True (Pydantic ConfigDict), making instances
        immutable after creation. This provides thread safety guarantees:
        once an instance is created and validated, its state cannot be
        modified, allowing safe sharing across threads without locks.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Validator identification
    # ONEX_EXCLUDE: string_id - human-readable validator identifier for YAML config
    validator_id: str = Field(
        ...,
        description="Unique identifier for this validator",
        min_length=1,
    )

    validator_name: str = Field(
        ...,
        description="Human-readable name for this validator",
        min_length=1,
    )

    validator_description: str = Field(
        ...,
        description="Description of what this validator checks",
        min_length=1,
    )

    # File targeting
    target_patterns: list[str] = Field(
        default_factory=lambda: ["**/*.py"],
        description="Glob patterns for files to validate (e.g., ['**/*.py'])",
        min_length=1,
    )

    exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/venv/**",
            "**/.git/**",
        ],
        description="Glob patterns to exclude from validation",
    )

    # Rules configuration
    rules: list[ModelValidatorRule] = Field(
        default_factory=list,
        description="Configurable validation rules",
    )

    # Suppression
    suppression_comments: list[str] = Field(
        default_factory=lambda: ["# noqa:", "# type: ignore", "# validator-ok:"],
        description="Comment patterns that suppress violations on a line",
    )

    # Behavior configuration
    severity_default: EnumSeverity = Field(
        default=EnumSeverity.ERROR,
        description="Default severity for violations without explicit severity",
    )

    fail_on_error: bool = Field(
        default=True,
        description="Whether to return non-zero exit code on ERROR severity violations",
    )

    fail_on_warning: bool = Field(
        default=False,
        description="Whether to return non-zero exit code on WARNING severity violations",
    )

    max_violations: int = Field(
        default=0,
        description="Maximum violations before stopping (0 = unlimited)",
        ge=0,
    )

    # Optional configuration
    source_root: Path | None = Field(
        default=None,
        description="Base path for validation operations (defaults to cwd)",
    )

    parallel_execution: bool = Field(
        default=True,
        description="Enable parallel file processing for performance",
    )

    @model_validator(mode="after")
    def validate_target_patterns_not_empty(self) -> "ModelValidatorSubcontract":
        """Validate that at least one target pattern is specified.

        A validator without any target patterns would validate nothing,
        which is likely a configuration error.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If target_patterns is empty.
        """
        if not self.target_patterns:
            msg = "target_patterns must contain at least one glob pattern"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("target_patterns"),
                        "validator_id": ModelSchemaValue.from_value(self.validator_id),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_unique_rule_ids(self) -> "ModelValidatorSubcontract":
        """Validate that all rule IDs are unique.

        Duplicate rule IDs would cause ambiguous rule selection and
        configuration conflicts.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If duplicate rule IDs are found.
        """
        if not self.rules:
            return self

        seen_ids: set[str] = set()
        duplicates: set[str] = set()

        for rule in self.rules:
            if rule.rule_id in seen_ids:
                duplicates.add(rule.rule_id)
            seen_ids.add(rule.rule_id)

        if duplicates:
            msg = f"Duplicate rule IDs found: {sorted(duplicates)}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("rules"),
                        "duplicates": ModelSchemaValue.from_value(
                            str(sorted(duplicates)),
                        ),
                        "validator_id": ModelSchemaValue.from_value(self.validator_id),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_fail_on_warning_implies_fail_on_error(
        self,
    ) -> "ModelValidatorSubcontract":
        """Validate that fail_on_warning implies fail_on_error.

        If fail_on_warning is True but fail_on_error is False, warnings
        would cause failure but errors would not, which is illogical.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If fail_on_warning is True but fail_on_error is False.
        """
        if self.fail_on_warning and not self.fail_on_error:
            msg = (
                "fail_on_error must be True when fail_on_warning is True "
                "(warnings cannot cause failure if errors do not)"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "fail_on_error": ModelSchemaValue.from_value(
                            str(self.fail_on_error),
                        ),
                        "fail_on_warning": ModelSchemaValue.from_value(
                            str(self.fail_on_warning),
                        ),
                        "validator_id": ModelSchemaValue.from_value(self.validator_id),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_suppression_patterns_not_empty_strings(
        self,
    ) -> "ModelValidatorSubcontract":
        """Validate that suppression patterns are not empty strings.

        Empty suppression patterns would match every line, which would
        suppress all violations and is likely a configuration error.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If any suppression pattern is an empty string.
        """
        empty_patterns = [p for p in self.suppression_comments if not p.strip()]
        if empty_patterns:
            msg = "suppression_comments cannot contain empty strings"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("suppression_comments"),
                        "validator_id": ModelSchemaValue.from_value(self.validator_id),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_source_root_no_traversal(self) -> "ModelValidatorSubcontract":
        """Validate that source_root does not contain path traversal sequences.

        Security: Prevents path traversal attacks via malicious YAML contracts
        that could specify source_root values like '../../../etc' to escape
        the intended validation directory.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If source_root contains path traversal patterns.
        """
        if self.source_root is None:
            return self

        path_str = str(self.source_root)

        # Security: Reject paths with traversal sequences
        # Check for parent directory traversal (..) and double slashes (//)
        #
        # SECURITY ASSUMPTION (OMN-1291):
        # This validation provides defense-in-depth for path traversal attacks.
        # It is the FIRST LINE of defense - catching malicious paths during model
        # construction from YAML contracts. Additional defense exists in:
        # - ValidatorBase._validate_cli_path() for CLI-provided paths
        # - ValidatorBase._resolve_targets() as a second check before file access
        #
        # Attack Vector: Malicious YAML contracts could specify source_root values
        # like '../../../etc' to escape the intended validation directory and
        # potentially access sensitive system files.
        #
        # Patterns detected (security hardening for multiple encoding variants):
        # - '..'       : Parent directory traversal (../../../etc/passwd)
        # - '//'       : Double slash (path bypass attempts)
        # - '%2e%2e%2f': URL-encoded ../ (full encoding bypass)
        # - '%2e%2e/'  : Partial URL encoding (mixed encoding bypass)
        # - '..%2f'    : Partial URL encoding (mixed encoding bypass)
        # - '..\\'     : Windows-style backslash traversal
        # - '.\\.\\'   : Windows dot-backslash traversal variant
        #
        # These patterns cover common evasion techniques attackers use to bypass
        # naive path validation that only checks for literal '..' sequences.
        traversal_patterns = [
            "..",  # Parent directory traversal
            "//",  # Double slash bypass
            "%2e%2e%2f",  # URL-encoded ../
            "%2e%2e/",  # Partial URL encoding
            "..%2f",  # Partial URL encoding variant
            "..\\",  # Windows backslash traversal
            ".\\.\\",  # Windows dot-backslash variant
        ]
        for pattern in traversal_patterns:
            if pattern in path_str:
                msg = f"source_root contains path traversal sequence: {pattern}"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("securityerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "path_traversal_check",
                            ),
                            "field": ModelSchemaValue.from_value("source_root"),
                            "pattern_detected": ModelSchemaValue.from_value(pattern),
                            "validator_id": ModelSchemaValue.from_value(
                                self.validator_id
                            ),
                        },
                    ),
                )
        # Security validated: source_root does not contain traversal patterns
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        frozen=True,  # Immutability after creation for thread safety
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        from_attributes=True,  # Required for pytest-xdist parallel execution
    )


__all__ = ["ModelValidatorSubcontract"]

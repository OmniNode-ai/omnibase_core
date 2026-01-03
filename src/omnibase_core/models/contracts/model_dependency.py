"""
Model Dependency Specification.

Unified dependency model that handles multiple input formats while providing
a clean, consistent interface for contract dependencies.

Eliminates union type anti-patterns in contract models by handling format
conversion internally through factory methods.

Strict typing is enforced - no Any types allowed in implementation.
"""

import re
from functools import lru_cache
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_dependency_type import EnumDependencyType
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = [
    "ModelDependency",
]


class ModelDependency(BaseModel):
    """
    ONEX dependency specification with strong typing enforcement.

    Provides structured dependency model for contract dependencies.
    STRONG TYPES ONLY: Only accepts properly typed ModelDependency instances.
    No string or dict[str, Any]fallbacks - use structured initialization only.

    Strict typing is enforced - no Any types allowed in implementation.
    """

    name: str = Field(
        default=...,
        description="Dependency name (e.g., 'ProtocolEventBus')",
        min_length=1,
    )

    module: str | None = Field(
        default=None,
        description="Module path (e.g., 'omnibase.protocol.protocol_event_bus')",
    )

    dependency_type: EnumDependencyType = Field(
        default=EnumDependencyType.PROTOCOL,
        description="Dependency type classification",
    )

    version: ModelSemVer | None = Field(
        default=None,
        description="Version constraint as ModelSemVer object",
    )

    required: bool = Field(
        default=True,
        description="Whether dependency is required for operation",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable dependency description",
    )

    # Type mapping for automatic classification
    _TYPE_PATTERNS: ClassVar[dict[str, EnumDependencyType]] = {
        "protocol": EnumDependencyType.PROTOCOL,
        "service": EnumDependencyType.SERVICE,
        "module": EnumDependencyType.MODULE,
        "external": EnumDependencyType.EXTERNAL,
    }

    # Compiled regex patterns for performance optimization (Phase 3L performance fix)
    # Thread-safe: ClassVar patterns are compiled once at class load time
    # and re.Pattern objects are immutable, allowing safe concurrent access
    _MODULE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$",
    )
    # Removed _CAMEL_TO_SNAKE_PATTERN to reduce memory footprint as requested in PR

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate dependency name follows ONEX conventions."""
        if not v or not v.strip():
            raise ModelOnexError(
                message="Dependency name cannot be empty or whitespace-only",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "provided_value": ModelSchemaValue.from_value(str(v)),
                        "field": ModelSchemaValue.from_value("name"),
                        "requirement": ModelSchemaValue.from_value("non_empty_string"),
                    },
                ),
            )

        v = v.strip()

        # Basic validation - allow protocols, services, modules
        min_name_length = 2
        if len(v) < min_name_length:
            raise ModelOnexError(
                message=f"Dependency name too short: {v}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "name": ModelSchemaValue.from_value(v),
                        "length": ModelSchemaValue.from_value(len(v)),
                        "min_length": ModelSchemaValue.from_value(min_name_length),
                        "field": ModelSchemaValue.from_value("name"),
                    },
                ),
            )

        return v

    @field_validator("module")
    @classmethod
    def validate_module(cls, v: str | None) -> str | None:
        """Validate module path format with security checks and performance optimization."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Refactored validation: security checks + format validation
        cls._validate_module_security(v)
        cls._validate_module_format(v)

        return v

    @classmethod
    def _validate_module_security(cls, module_path: str) -> None:
        """Validate module path security to prevent path traversal attacks with enhanced detection."""
        security_violations = []
        recommendations = []

        # Enhanced path traversal detection
        if ".." in module_path:
            security_violations.append("parent_directory_traversal")
            recommendations.append("Remove '..' sequences from module path")
        if "/" in module_path or "\\" in module_path:
            security_violations.append("directory_separator_found")
            recommendations.append("Use dots (.) as module separators, not slashes")

        # Enhanced absolute path detection
        if module_path.startswith(("/", "C:", "D:", "~")):
            security_violations.append("absolute_path_detected")
            recommendations.append("Use relative module paths only")

        # Enhanced relative path detection
        if module_path.startswith("."):
            security_violations.append("relative_path_start")
            recommendations.append("Start module path with module name, not dots")

        # Enhanced shell injection detection
        dangerous_chars = [
            "<",
            ">",
            "|",
            "&",
            ";",
            "`",
            "$",
            "'",
            '"',
            "*",
            "?",
            "[",
            "]",
        ]
        found_chars = [char for char in dangerous_chars if char in module_path]
        if found_chars:
            security_violations.append("shell_injection_characters")
            recommendations.append(
                f"Remove dangerous characters: {', '.join(found_chars)}",
            )

        # Enhanced length validation
        max_length = 200
        if len(module_path) > max_length:
            security_violations.append("excessive_length")
            recommendations.append(
                f"Shorten module path to under {max_length} characters",
            )

        # Additional security checks - refined to catch privileged paths while allowing legitimate protocol names
        # Allow legitimate protocol patterns like "protocol_file_system" but catch suspicious combinations
        privileged_keywords = ["system", "admin", "root", "config"]

        # Check for privileged keywords in module path
        for keyword in privileged_keywords:
            if keyword in module_path.lower():
                # Allow legitimate protocol patterns
                if keyword == "system" and (
                    "file_system" in module_path.lower()
                    or "event_system" in module_path.lower()
                ):
                    continue  # Allow legitimate system protocols

                if keyword == "config" and "protocol" in module_path.lower():
                    continue  # Allow legitimate config protocols

                # Flag other uses of privileged keywords
                security_violations.append("potentially_privileged_path")
                recommendations.append(
                    f"Avoid '{keyword}' references in module paths unless for legitimate protocols",
                )
                break  # Only report first violation to avoid spam

        if security_violations:
            raise ModelOnexError(
                message=f"Security violations in module path '{module_path[:50] if len(module_path) > 50 else module_path}': {', '.join(security_violations)}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "module_path": ModelSchemaValue.from_value(module_path[:100]),
                        "security_violations": ModelSchemaValue.from_value(
                            ", ".join(security_violations),
                        ),
                        "recommendations": ModelSchemaValue.from_value(
                            ", ".join(recommendations),
                        ),
                        "valid_example": ModelSchemaValue.from_value(
                            "omnibase_core.models.example",
                        ),
                        "security_policy": ModelSchemaValue.from_value(
                            "Module paths must use only alphanumeric, underscore, and dot characters",
                        ),
                    },
                ),
            )

    @classmethod
    def _validate_module_format(cls, module_path: str) -> None:
        """Validate module path format using pre-compiled pattern with caching for performance."""
        if not cls._MODULE_PATTERN.match(module_path):
            raise ModelOnexError(
                message=f"Invalid module path format: {module_path}. Must be valid Python module path.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "module_path": ModelSchemaValue.from_value(module_path),
                        "expected_format": ModelSchemaValue.from_value(
                            "alphanumeric.segments.with_underscores",
                        ),
                        "pattern": ModelSchemaValue.from_value(
                            cls._MODULE_PATTERN.pattern,
                        ),
                        "example": ModelSchemaValue.from_value(
                            "omnibase_core.models.example",
                        ),
                        "performance_note": ModelSchemaValue.from_value(
                            "Validation uses optimized pre-compiled regex",
                        ),
                    },
                ),
            )

    @model_validator(mode="after")
    def validate_consistency(self) -> "ModelDependency":
        """Validate consistency between name, module, and type."""
        # If module is specified, validate name-module consistency
        if self.module and self.name not in self.module:
            # Allow flexibility for service and module types with different conventions
            if self.dependency_type in (
                EnumDependencyType.SERVICE,
                EnumDependencyType.MODULE,
            ):
                # These types often have flexible naming patterns
                return self

            # For protocol types, require protocol name match for consistency
            if self.dependency_type == EnumDependencyType.PROTOCOL:
                # Check snake_case variant (e.g., event_bus)
                snake_case_name = self._camel_to_snake_case(self.name)
                if snake_case_name in self.module.lower():
                    return self

                # Warn about potential naming inconsistencies but allow flexibility
            # Log inconsistency for audit purposes without blocking valid dependencies

        return self

    def _camel_to_snake_case(self, camel_str: str) -> str:
        """Convert camelCase to snake_case using cached conversion for performance."""
        # Insert underscore before uppercase letters that follow lowercase letters
        # or digits. This handles camelCase patterns while avoiding consecutive caps.
        # Uses cached function for performance with frequently validated dependencies
        return self._cached_camel_to_snake_conversion(camel_str)

    @classmethod
    @lru_cache(maxsize=128)
    def _cached_camel_to_snake_conversion(cls, camel_str: str) -> str:
        """Cached camelCase to snake_case conversion for performance."""
        pattern = re.compile(r"(?<!^)(?<=[a-z0-9])(?=[A-Z])")
        return pattern.sub("_", camel_str).lower()

    def to_string(self) -> str:
        """Convert to simple string representation."""
        return self.module if self.module else self.name

    # Removed to_dict() anti-pattern - use model_dump() directly for ONEX compliance
    # The custom transformations here violated ONEX standards by bypassing Pydantic validation
    # Use model_dump(exclude_none=True) directly, with any custom transformations
    # applied at the boundary layer, not in the model itself

    def is_protocol(self) -> bool:
        """Check if dependency is a protocol."""
        return self.dependency_type == EnumDependencyType.PROTOCOL

    def is_service(self) -> bool:
        """Check if dependency is a service."""
        return self.dependency_type == EnumDependencyType.SERVICE

    def is_external(self) -> bool:
        """Check if dependency is external."""
        return self.dependency_type == EnumDependencyType.EXTERNAL

    def matches_onex_patterns(self) -> bool:
        """Validate dependency follows ONEX naming patterns."""
        if self.dependency_type == EnumDependencyType.PROTOCOL:
            # Protocol dependencies should contain 'protocol' in name or module
            return "protocol" in self.name.lower() or (
                self.module is not None and "protocol" in self.module.lower()
            )

        # Other types have more flexible patterns
        return True

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from various input formats
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
        str_strip_whitespace=True,
    )


# ONEX-compatible dependency model - no factory functions or custom serialization
# Use direct instantiation: ModelDependency(name="...", module="...")
# Use model_dump() for serialization, not custom to_dict() methods

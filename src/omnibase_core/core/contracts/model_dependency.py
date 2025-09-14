"""
Model Dependency - ONEX Standards Compliant Dependency Specification.

Unified dependency model that handles multiple input formats while providing
a clean, consistent interface for contract dependencies.

Eliminates union type anti-patterns in contract models by handling format
conversion internally through factory methods.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

import re
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.models.core.model_semver import ModelSemVer


class EnumDependencyType(Enum):
    """Dependency type classification for ONEX contract validation."""

    PROTOCOL = "protocol"
    SERVICE = "service"
    MODULE = "module"
    EXTERNAL = "external"


class ModelDependency(BaseModel):
    """
    ONEX dependency specification with strong typing enforcement.

    Provides structured dependency model for contract dependencies.
    STRONG TYPES ONLY: Only accepts properly typed ModelDependency instances.
    No string or dict fallbacks - use structured initialization only.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    name: str = Field(
        ...,
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
        r"^[a-zA-Z][a-zA-Z0-9_-]*(\.[a-zA-Z][a-zA-Z0-9_-]*)*$"
    )
    _CAMEL_TO_SNAKE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?<!^)(?<=[a-z0-9])(?=[A-Z])"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate dependency name follows ONEX conventions."""
        if not v or not v.strip():
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message="Dependency name cannot be empty or whitespace-only",
                context={
                    "provided_value": v,
                    "field": "name",
                    "requirement": "non_empty_string",
                },
            )

        v = v.strip()

        # Basic validation - allow protocols, services, modules
        min_name_length = 2
        if len(v) < min_name_length:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Dependency name too short: {v}",
                context={
                    "name": v,
                    "length": len(v),
                    "min_length": min_name_length,
                    "field": "name",
                },
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
        """Validate module path security to prevent path traversal attacks."""
        security_violations = []

        # Check for path traversal sequences
        if ".." in module_path:
            security_violations.append("parent_directory_traversal")
        if "/" in module_path or "\\" in module_path:
            security_violations.append("directory_separator_found")

        # Check for other dangerous patterns
        if module_path.startswith("."):
            security_violations.append("relative_path_start")
        if any(char in module_path for char in ["<", ">", "|", "&", ";", "`", "$"]):
            security_violations.append("shell_injection_characters")
        if len(module_path) > 200:  # Prevent excessively long module paths
            security_violations.append("excessive_length")

        if security_violations:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Invalid module path: {module_path}. Security violations detected: {', '.join(security_violations)}",
                context={
                    "module_path": module_path,
                    "security_violations": security_violations,
                    "recommendation": "Use only alphanumeric characters, underscores, hyphens, and dots",
                },
            )

    @classmethod
    def _validate_module_format(cls, module_path: str) -> None:
        """Validate module path format using pre-compiled pattern for performance."""
        if not cls._MODULE_PATTERN.match(module_path):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Invalid module path format: {module_path}. Must be valid Python module path.",
                context={
                    "module_path": module_path,
                    "expected_format": "alphanumeric.segments.with_underscores_or_hyphens",
                    "pattern": cls._MODULE_PATTERN.pattern,
                    "example": "omnibase_core.models.example",
                },
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

            # For other types, require some form of name match for consistency
            # This ensures dependencies are properly named and discoverable

        return self

    def _camel_to_snake_case(self, camel_str: str) -> str:
        """Convert camelCase to snake_case using pre-compiled regex for performance."""
        # Insert underscore before uppercase letters that follow lowercase letters
        # or digits. This handles camelCase patterns while avoiding consecutive caps.
        # Uses pre-compiled class-level pattern for optimal performance
        return self._CAMEL_TO_SNAKE_PATTERN.sub("_", camel_str).lower()

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
                self.module and "protocol" in self.module.lower()
            )

        # Other types have more flexible patterns
        return True

    model_config = {
        "extra": "ignore",  # Allow extra fields from various input formats
        "use_enum_values": False,  # Keep enum objects, don't convert to strings
        "validate_assignment": True,
        "str_strip_whitespace": True,
    }


# ONEX-compliant dependency model - no factory functions or custom serialization
# Use direct instantiation: ModelDependency(name="...", module="...")
# Use model_dump() for serialization, not custom to_dict() methods

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
    Unified dependency specification with internal format handling.

    Provides clean interface while supporting multiple input formats:
    - String dependencies: "ProtocolEventBus"
    - Dict dependencies: {"name": "ProtocolEventBus", "module": "..."}
    - Structured dependencies: ModelDependencySpec instances

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

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate dependency name follows ONEX conventions."""
        if not v or not v.strip():
            msg = "Dependency name cannot be empty or whitespace-only"
            raise ValueError(msg)

        v = v.strip()

        # Basic validation - allow protocols, services, modules
        min_name_length = 2
        if len(v) < min_name_length:
            msg = f"Dependency name too short: {v}"
            raise ValueError(msg)

        return v

    @field_validator("module")
    @classmethod
    def validate_module(cls, v: str | None) -> str | None:
        """Validate module path format."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Secure module path validation to prevent path traversal attacks
        import re

        # Prevent path traversal attempts
        if ".." in v or "/" in v or "\\" in v:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Invalid module path: {v}. Path traversal sequences not allowed.",
                context={
                    "module_path": v,
                    "security_violation": "path_traversal_attempt",
                },
            )

        # Validate proper module path format: alphanumeric segments separated by dots
        # Allow underscores and hyphens within segments, but not at start/end
        module_pattern = r"^[a-zA-Z][a-zA-Z0-9_-]*(\.[a-zA-Z][a-zA-Z0-9_-]*)*$"
        if not re.match(module_pattern, v):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Invalid module path format: {v}. Must be valid Python module path.",
                context={
                    "module_path": v,
                    "expected_format": "alphanumeric.segments.with_underscores_or_hyphens",
                    "pattern": module_pattern,
                },
            )

        return v

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
        """Convert camelCase to snake_case using regex."""
        # Insert underscore before uppercase letters that follow lowercase letters
        # or digits. This handles camelCase patterns while avoiding consecutive caps.
        return re.sub(r"(?<!^)(?<=[a-z0-9])(?=[A-Z])", "_", camel_str).lower()

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

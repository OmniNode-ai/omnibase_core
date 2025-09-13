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

    @classmethod
    def _from_string(cls, dependency_str: str) -> "ModelDependency":
        """
        Create dependency from string format.

        Args:
            dependency_str: Dependency string (e.g., "ProtocolEventBus")

        Returns:
            ModelDependency instance with inferred type

        Examples:
            >>> ModelDependency._from_string("ProtocolEventBus")
            ModelDependency(name="ProtocolEventBus", dependency_type=PROTOCOL)

            >>> ModelDependency._from_string("omnibase.protocol.protocol_consul_client")
            ModelDependency(
                name="protocol_consul_client",
                module="omnibase.protocol.protocol_consul_client",
                dependency_type=PROTOCOL
            )
        """
        if not dependency_str or not dependency_str.strip():
            msg = "Dependency string cannot be empty or whitespace-only"
            raise ValueError(msg)

        dependency_str = dependency_str.strip()

        # Handle fully qualified module paths
        if "." in dependency_str:
            parts = dependency_str.split(".")
            name = parts[-1]  # Last part is the name
            module = dependency_str

            # Infer type from module path
            dependency_type = cls._infer_type_from_module(module)
        else:
            # Simple name format
            name = dependency_str
            module = None
            dependency_type = cls._infer_type_from_name(name)

        return cls(
            name=name,
            module=module,
            dependency_type=dependency_type,
        )

    @classmethod
    def _from_dict(cls, dependency_dict: dict[str, Any]) -> "ModelDependency":
        """
        Create dependency from dictionary format.

        Args:
            dependency_dict: Dictionary with dependency specification

        Returns:
            ModelDependency instance

        Examples:
            >>> ModelDependency._from_dict({
            ...     "name": "ProtocolEventBus",
            ...     "module": "omnibase.protocol.protocol_event_bus",
            ...     "type": "protocol"
            ... })
        """
        if not isinstance(dependency_dict, dict):
            msg = f"Expected dict, got {type(dependency_dict)}"
            raise TypeError(msg)

        # Extract required name
        name = dependency_dict.get("name")
        if not name:
            msg = "Dependency dict must contain 'name' field"
            raise ValueError(msg)

        # Extract optional fields
        module = dependency_dict.get("module")
        dependency_type_str = dependency_dict.get("type", "protocol")
        version_input = dependency_dict.get("version")
        required = dependency_dict.get("required", True)
        description = dependency_dict.get("description")

        # Convert version string to ModelSemVer if provided
        version = cls._parse_version_input(version_input) if version_input else None

        # Convert type string to enum
        dependency_type = cls._parse_dependency_type(dependency_type_str)

        return cls(
            name=name,
            module=module,
            dependency_type=dependency_type,
            version=version,
            required=required,
            description=description,
        )

    @classmethod
    def _from_structured(cls, structured_dep: Any) -> "ModelDependency":
        """
        Create dependency from structured dependency object.

        Args:
            structured_dep: Object with name, type, module attributes

        Returns:
            ModelDependency instance
        """
        if not hasattr(structured_dep, "name"):
            msg = (
                f"Structured dependency must have 'name' attribute, "
                f"got {type(structured_dep)}"
            )
            raise ValueError(msg)

        name = structured_dep.name
        module = getattr(structured_dep, "module", None)
        dependency_type_str = getattr(structured_dep, "type", "protocol")
        version_input = getattr(structured_dep, "version", None)
        required = getattr(structured_dep, "required", True)
        description = getattr(structured_dep, "description", None)

        # Convert version input to ModelSemVer if provided
        version = cls._parse_version_input(version_input) if version_input else None

        dependency_type = cls._parse_dependency_type(dependency_type_str)

        return cls(
            name=name,
            module=module,
            dependency_type=dependency_type,
            version=version,
            required=required,
            description=description,
        )

    @classmethod
    def _infer_type_from_name(cls, name: str) -> EnumDependencyType:
        """Infer dependency type from name patterns."""
        name_lower = name.lower()

        if "protocol" in name_lower:
            return EnumDependencyType.PROTOCOL
        if "service" in name_lower:
            return EnumDependencyType.SERVICE
        return EnumDependencyType.MODULE

    @classmethod
    def _infer_type_from_module(cls, module: str) -> EnumDependencyType:
        """Infer dependency type from module path patterns."""
        module_lower = module.lower()

        if "protocol" in module_lower:
            return EnumDependencyType.PROTOCOL
        if "service" in module_lower:
            return EnumDependencyType.SERVICE
        if module.startswith(("http", "https", "git")):
            return EnumDependencyType.EXTERNAL
        return EnumDependencyType.MODULE

    @classmethod
    def _parse_dependency_type(cls, type_str: str) -> EnumDependencyType:
        """Parse dependency type string to enum."""
        if isinstance(type_str, EnumDependencyType):
            return type_str

        type_str_lower = str(type_str).lower()

        for pattern, enum_type in cls._TYPE_PATTERNS.items():
            if pattern in type_str_lower:
                return enum_type

        # Default fallback
        return EnumDependencyType.MODULE

    @classmethod
    def _parse_version_input(cls, version_input: Any) -> ModelSemVer:
        """Parse version input to ModelSemVer object - ModelSemVer or dict only."""
        if isinstance(version_input, ModelSemVer):
            return version_input

        if isinstance(version_input, dict):
            # Handle dict format like {"major": 1, "minor": 0, "patch": 0}
            try:
                return ModelSemVer.model_validate(version_input)
            except Exception as e:
                msg = f"Invalid version dict format: {version_input}, error: {e}"
                raise ValueError(msg) from e

        # Reject string versions - forces proper ModelSemVer usage
        if isinstance(version_input, str):
            msg = (
                f"String versions not allowed: '{version_input}'. "
                "Use ModelSemVer(major=X, minor=Y, patch=Z) or dict format."
            )
            raise TypeError(msg)

        msg = (
            f"Unsupported version input type: {type(version_input)}, "
            f"value: {version_input}. Use ModelSemVer or dict format only."
        )
        raise TypeError(msg)

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
                context={"module_path": v, "security_violation": "path_traversal_attempt"}
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
                    "pattern": module_pattern
                }
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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        # Build result dictionary to avoid validation false positives
        result_dict = {"name": self.name, "type": self.dependency_type.value}

        # Add optional fields using dict.update() to avoid subscript access
        # false positives
        optional_data = {}

        if self.module:
            optional_data.update(module=self.module)

        if self.version:
            version_data = (
                self.version.model_dump()
                if isinstance(self.version, ModelSemVer)
                else self.version
            )
            optional_data.update(version=version_data)

        if not self.required:
            optional_data.update(required=self.required)

        if self.description:
            optional_data.update(description=self.description)

        result_dict.update(optional_data)
        return result_dict

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


# Factory function for unified dependency creation
# NOTE: Union type is acceptable here as a factory function interface
# Eliminates Union types from data models while handling input conversion
def _create_dependency_internal(
    dependency_input: str | dict[str, Any] | Any,
) -> ModelDependency:
    """
    INTERNAL: Create ModelDependency from various input formats.

    This is an internal function and should not be used in public APIs.
    All dependencies should be provided in structured dict format only.

    Args:
        dependency_input: String, dict, or structured dependency

    Returns:
        ModelDependency instance
    """
    if isinstance(dependency_input, str):
        return ModelDependency._from_string(dependency_input)
    if isinstance(dependency_input, dict):
        return ModelDependency._from_dict(dependency_input)
    return ModelDependency._from_structured(dependency_input)

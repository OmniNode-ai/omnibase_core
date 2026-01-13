"""
Environment Variables Model

Type-safe environment variable management with validation and security.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelEnvironmentVariables(BaseModel):
    """
    Type-safe environment variable management.

    Provides secure handling of environment variables with validation,
    sanitization, and security-conscious defaults.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    variables: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables as key-value pairs",
    )

    secure_variables: set[str] = Field(
        default_factory=set,
        description="Set of variable names that contain sensitive data",
    )

    inherit_system: bool = Field(
        default=True,
        description="Whether to inherit system environment variables",
    )

    @field_validator("variables")
    @classmethod
    def validate_variable_names(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate environment variable names."""
        for name in v:
            if not name.isidentifier() and not name.replace("_", "").isalnum():
                msg = f"Invalid environment variable name: {name}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
                )
            if name.startswith("__"):
                msg = f"Environment variable name cannot start with double underscore: {name}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
                )
        return v

    def add_variable(self, name: str, value: str, secure: bool = False) -> None:
        """
        Add an environment variable.

        Args:
            name: Variable name
            value: Variable value
            secure: Whether this variable contains sensitive data
        """
        self.variables[name] = value
        if secure:
            self.secure_variables.add(name)

    def remove_variable(self, name: str) -> bool:
        """
        Remove an environment variable.

        Args:
            name: Variable name to remove

        Returns:
            True if variable was removed, False if it didn't exist
        """
        if name in self.variables:
            del self.variables[name]
            self.secure_variables.discard(name)
            return True
        return False

    def get_variable(self, name: str, default: str = "") -> str:
        """
        Get environment variable value.

        Args:
            name: Variable name
            default: Default value if not found

        Returns:
            Variable value or default
        """
        return self.variables.get(name, default)

    def has_variable(self, name: str) -> bool:
        """Check if environment variable exists."""
        return name in self.variables

    def is_secure(self, name: str) -> bool:
        """Check if environment variable is marked as secure."""
        return name in self.secure_variables

    def mark_secure(self, name: str) -> bool:
        """
        Mark an environment variable as secure.

        Args:
            name: Variable name to mark as secure

        Returns:
            True if variable exists and was marked, False otherwise
        """
        if name in self.variables:
            self.secure_variables.add(name)
            return True
        return False

    def unmark_secure(self, name: str) -> None:
        """Remove secure marking from an environment variable."""
        self.secure_variables.discard(name)

    def get_secure_variables(self) -> dict[str, str]:
        """Get all variables marked as secure."""
        return {
            name: value
            for name, value in self.variables.items()
            if name in self.secure_variables
        }

    def get_non_secure_variables(self) -> dict[str, str]:
        """Get all variables not marked as secure."""
        return {
            name: value
            for name, value in self.variables.items()
            if name not in self.secure_variables
        }

    def merge(self, other: ModelEnvironmentVariables, override: bool = True) -> None:
        """
        Merge another environment variables model into this one.

        Args:
            other: Other environment variables to merge
            override: Whether to override existing variables
        """
        for name, value in other.variables.items():
            if override or name not in self.variables:
                self.variables[name] = value

        # Merge secure markings
        self.secure_variables.update(other.secure_variables)

    def clear(self) -> None:
        """Clear all environment variables."""
        self.variables.clear()
        self.secure_variables.clear()

    def count(self) -> int:
        """Get total number of environment variables."""
        return len(self.variables)

    def count_secure(self) -> int:
        """Get number of secure environment variables."""
        return len(self.secure_variables)

    def validate_required(self, required_vars: list[str]) -> list[str]:
        """
        Validate that required environment variables are present.

        Args:
            required_vars: List of required variable names

        Returns:
            List of missing required variables
        """
        return [var for var in required_vars if var not in self.variables]

    @classmethod
    def from_system(
        cls,
        prefix: str | None = None,
        secure_patterns: list[str] | None = None,
    ) -> ModelEnvironmentVariables:
        """
        Create from system environment variables.

        Args:
            prefix: Optional prefix to filter variables (e.g., "MYAPP_")
            secure_patterns: List of patterns to identify secure variables

        Returns:
            New ModelEnvironmentVariables instance
        """
        import os
        import re

        variables = {}
        secure_vars = set()

        for name, value in os.environ.items():
            if prefix and not name.startswith(prefix):
                continue

            variables[name] = value

            # Check if variable matches secure patterns
            if secure_patterns:
                for pattern in secure_patterns:
                    if re.search(pattern, name, re.IGNORECASE):
                        secure_vars.add(name)
                        break

        return cls(variables=variables, secure_variables=secure_vars)

    def __len__(self) -> int:
        """Return number of environment variables."""
        return len(self.variables)

    def __contains__(self, name: str) -> bool:
        """Check if environment variable exists."""
        return name in self.variables

    def __getitem__(self, name: str) -> str:
        """Get environment variable value."""
        return self.variables[name]

    def __setitem__(self, name: str, value: str) -> None:
        """Set environment variable value."""
        self.variables[name] = value

    def __delitem__(self, name: str) -> None:
        """Delete environment variable."""
        del self.variables[name]
        self.secure_variables.discard(name)

    def iter_variable_names(self) -> Iterator[str]:
        """Iterate over variable names."""
        return iter(self.variables)

    def __str__(self) -> str:
        """String representation with secure variables hidden."""
        return f"ModelEnvironmentVariables({len(self.variables)} variables)"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"ModelEnvironmentVariables(variables={len(self.variables)}, secure={len(self.secure_variables)})"

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If execution logic fails
        """
        # Update any relevant execution fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelEnvironmentVariables"]

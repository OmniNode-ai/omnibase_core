"""Protocol dependency model for contract-driven DI.

Defines protocol dependency declarations in contract.yaml for zero-code
node base classes. Enables declarative dependency injection where protocols
are resolved from the container at node initialization.

VERSION: 1.0.0

Author: ONEX Framework Team
"""

from __future__ import annotations

import re
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelProtocolDependency(BaseModel):
    """
    Protocol dependency declaration for contract-driven dependency injection.

    Declares a protocol that a node requires from the DI container. At node
    initialization, the framework resolves each declared protocol and binds
    it to the node's protocol namespace.

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.

    Examples:
        >>> dep = ModelProtocolDependency(
        ...     name="ProtocolEventBus",
        ...     protocol="omnibase_core.protocols.protocol_event_bus:ProtocolEventBus",
        ... )
        >>> dep.get_bind_name()
        'event_bus'

        >>> dep = ModelProtocolDependency(
        ...     name="ProtocolLogger",
        ...     protocol="omnibase_core.protocols.protocol_logger:ProtocolLogger",
        ...     bind_as="log",
        ... )
        >>> dep.get_bind_name()
        'log'

    YAML Example:
        .. code-block:: yaml

            protocol_dependencies:
              - name: ProtocolEventBus
                protocol: omnibase_core.protocols.protocol_event_bus:ProtocolEventBus
                required: true
              - name: ProtocolLogger
                protocol: omnibase_core.protocols.protocol_logger:ProtocolLogger
                bind_as: log
                required: false
    """

    # Pattern for valid Python identifiers (PEP 3131 simplified)
    IDENTIFIER_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[a-zA-Z_][a-zA-Z0-9_]*$"
    )

    # Pattern for protocol import path: module.path:ClassName
    # Module path: dotted Python module path (e.g., omnibase_core.protocols.protocol_event_bus)
    # Class name: valid Python identifier after colon
    PROTOCOL_PATH_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?P<module>[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)"
        r":(?P<class>[a-zA-Z_][a-zA-Z0-9_]*)$"
    )

    name: str
    """Container registration name (e.g., 'ProtocolLogger')."""

    protocol: str
    """Import path in 'module.path:ClassName' format."""

    required: bool = True
    """If True, fail fast when dependency is missing from container."""

    bind_as: str | None = None
    """Optional alias for self.protocols namespace. If None, derived from name."""

    lazy_import: bool = False
    """If True, defer protocol resolution for cold-start optimization."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> str:
        """
        Validate that name is a non-empty valid Python identifier.

        Args:
            value: The name value to validate.

        Returns:
            The validated name string.

        Raises:
            ModelOnexError: If name is empty or not a valid identifier.
        """
        if not isinstance(value, str):
            raise ModelOnexError(
                message=f"Protocol dependency name must be a string, got {type(value).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if not value:
            raise ModelOnexError(
                message="Protocol dependency name cannot be empty",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if not cls.IDENTIFIER_PATTERN.match(value):
            raise ModelOnexError(
                message=f"Protocol dependency name must be a valid Python identifier: {value!r}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                name=value,
            )

        return value

    @field_validator("protocol", mode="before")
    @classmethod
    def validate_protocol(cls, value: object) -> str:
        """
        Validate that protocol follows 'module.path:ClassName' format.

        Args:
            value: The protocol import path to validate.

        Returns:
            The validated protocol string.

        Raises:
            ModelOnexError: If protocol format is invalid.
        """
        if not isinstance(value, str):
            raise ModelOnexError(
                message=f"Protocol path must be a string, got {type(value).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if not value:
            raise ModelOnexError(
                message="Protocol path cannot be empty",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if ":" not in value:
            raise ModelOnexError(
                message=(
                    f"Protocol path must use colon-separated format 'module.path:ClassName', "
                    f"got: {value!r}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                protocol=value,
            )

        if not cls.PROTOCOL_PATH_PATTERN.match(value):
            raise ModelOnexError(
                message=(
                    f"Invalid protocol path format: {value!r}. "
                    "Expected format: 'module.path:ClassName' where module.path is a valid "
                    "dotted Python module path and ClassName is a valid identifier."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                protocol=value,
            )

        return value

    @field_validator("bind_as", mode="before")
    @classmethod
    def validate_bind_as(cls, value: object) -> str | None:
        """
        Validate that bind_as, if provided, is a valid Python identifier.

        Args:
            value: The bind_as alias to validate.

        Returns:
            The validated bind_as string or None.

        Raises:
            ModelOnexError: If bind_as is not a valid identifier.
        """
        if value is None:
            return None

        if not isinstance(value, str):
            raise ModelOnexError(
                message=f"bind_as must be a string or None, got {type(value).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if not value:
            # Empty string treated as None
            return None

        if not cls.IDENTIFIER_PATTERN.match(value):
            raise ModelOnexError(
                message=f"bind_as must be a valid Python identifier: {value!r}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                bind_as=value,
            )

        return value

    def get_bind_name(self) -> str:
        """
        Get the binding name for the protocols namespace.

        Returns the explicit bind_as if set, otherwise derives a snake_case
        name from the Protocol name by:
        1. Removing 'Protocol' prefix if present
        2. Converting PascalCase to snake_case

        Returns:
            The name to use in self.protocols namespace.

        Examples:
            >>> ModelProtocolDependency(
            ...     name="ProtocolEventBus",
            ...     protocol="m:C",
            ... ).get_bind_name()
            'event_bus'

            >>> ModelProtocolDependency(
            ...     name="ProtocolLogger",
            ...     protocol="m:C",
            ...     bind_as="log",
            ... ).get_bind_name()
            'log'

            >>> ModelProtocolDependency(
            ...     name="EventBus",
            ...     protocol="m:C",
            ... ).get_bind_name()
            'event_bus'
        """
        if self.bind_as:
            return self.bind_as

        # Derive from name, removing standard prefix for ergonomic binding
        # (e.g., ProtocolLogger -> logger, ProtocolEventBus -> event_bus)
        name = self.name.removeprefix("Protocol")

        # Convert PascalCase to snake_case
        return self._pascal_to_snake(name)

    @staticmethod
    def _pascal_to_snake(name: str) -> str:
        """
        Convert PascalCase to snake_case.

        Args:
            name: PascalCase string to convert.

        Returns:
            snake_case version of the input.

        Examples:
            >>> ModelProtocolDependency._pascal_to_snake("EventBus")
            'event_bus'
            >>> ModelProtocolDependency._pascal_to_snake("XMLParser")
            'xml_parser'
            >>> ModelProtocolDependency._pascal_to_snake("IOHandler")
            'io_handler'
        """
        if not name:
            return ""

        # Insert underscore before uppercase letters (except at start)
        # Handle consecutive uppercase (e.g., XMLParser -> xml_parser)
        result: list[str] = []
        for i, char in enumerate(name):
            if char.isupper():
                # Add underscore if not at start and either:
                # - Previous char is lowercase, OR
                # - Next char is lowercase (handles XMLParser -> xml_parser)
                if i > 0:
                    prev_lower = name[i - 1].islower()
                    next_lower = i + 1 < len(name) and name[i + 1].islower()
                    if prev_lower or next_lower:
                        result.append("_")
                result.append(char.lower())
            else:
                result.append(char)

        return "".join(result)

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return (
            f"ModelProtocolDependency(name={self.name!r}, "
            f"protocol={self.protocol!r}, required={self.required})"
        )


__all__ = ["ModelProtocolDependency"]

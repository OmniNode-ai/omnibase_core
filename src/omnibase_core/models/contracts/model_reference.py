# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Model Reference.

Reference to a Pydantic model type for input/output specifications in contracts.
Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation

.. versionadded:: 0.4.0
"""

import importlib
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "ModelReference",
]


class ModelReference(BaseModel):
    """Reference to a Pydantic model type for input/output specifications.

    Model references allow contracts and patches to specify input and output
    model types without importing the actual classes. Resolution happens at
    contract expansion time.

    Attributes:
        module: Python module path containing the model class.
        class_name: Name of the model class within the module.
        version: Optional version constraint for the model.

    Example:
        >>> ref = ModelReference(
        ...     module="omnibase_core.models.events",
        ...     class_name="ModelEventEnvelope",
        ...     version="1.0.0",
        ... )
        >>> ref.fully_qualified_name
        'omnibase_core.models.events.ModelEventEnvelope'

    See Also:
        - ModelContractPatch: Uses this for input_model and output_model fields
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    module: str = Field(
        ...,
        min_length=1,
        description=(
            "Python module path containing the model class "
            "(e.g., 'omnibase_core.models.events'). "
            "Leading/trailing whitespace is automatically stripped."
        ),
    )

    class_name: str = Field(
        ...,
        min_length=1,
        description=(
            "Name of the model class within the module (e.g., 'ModelEventEnvelope'). "
            "Leading/trailing whitespace is automatically stripped."
        ),
    )

    version: str | None = Field(
        default=None,
        description="Optional version constraint for the model (e.g., '1.0.0').",
    )

    @field_validator("module")
    @classmethod
    def validate_module_format(cls, v: str) -> str:
        """Validate module path format.

        Module paths must be valid Python dotted paths where each segment
        starts with a letter or underscore. Leading and trailing whitespace
        is stripped before validation.

        Args:
            v: The raw module path string.

        Returns:
            The validated and stripped module path.

        Raises:
            ValueError: If the path is empty, contains empty segments,
                or has segments starting with invalid characters.
        """
        v = v.strip()
        if not v:
            raise ValueError("Module path cannot be empty")

        # Basic validation - should be valid Python module path
        parts = v.split(".")
        for part in parts:
            if not part:
                raise ValueError(f"Invalid module path: {v}")
            if not part[0].isalpha() and part[0] != "_":
                raise ValueError(
                    f"Module path segments must start with letter or underscore: {v}"
                )

        return v

    @field_validator("class_name")
    @classmethod
    def validate_class_name(cls, v: str) -> str:
        """Validate class name format.

        Class names must follow Python naming conventions: non-empty and
        starting with an uppercase letter (PEP 8 class naming). Leading
        and trailing whitespace is stripped before validation.

        Args:
            v: The raw class name string.

        Returns:
            The validated and stripped class name.

        Raises:
            ValueError: If the name is empty or doesn't start with uppercase.
        """
        v = v.strip()
        if not v:
            raise ValueError("Class name cannot be empty")

        # Class names should start with uppercase letter (convention)
        if not v[0].isupper():
            raise ValueError(f"Class name should start with uppercase letter: {v}")

        return v

    @property
    def fully_qualified_name(self) -> str:
        """Get the fully qualified name (module.class_name)."""
        return f"{self.module}.{self.class_name}"

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        version_str = f", version={self.version!r}" if self.version else ""
        return f"ModelReference({self.fully_qualified_name!r}{version_str})"

    @classmethod
    def resolve_import(cls, reference: str) -> type | None:
        """Safely resolve a module/class reference from a fully qualified path.

        This method attempts to import the referenced module and retrieve the
        specified class. It handles common import errors gracefully by returning
        None rather than raising exceptions.

        Args:
            reference: Fully qualified module.class path
                (e.g., 'omnibase_core.models.events.ModelEventEnvelope')

        Returns:
            The resolved class/type, or None if resolution fails due to:
            - Invalid reference format (no module separator)
            - Module not found (ImportError)
            - Class not found in module (AttributeError)

        Example:
            >>> ModelReference.resolve_import('omnibase_core.models.events.ModelEventEnvelope')
            <class 'omnibase_core.models.events.ModelEventEnvelope'>
            >>> ModelReference.resolve_import('nonexistent.module.Class')
            None
        """
        if not reference or "." not in reference:
            return None

        try:
            module_path, class_name = reference.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name, None)
        except (ImportError, ValueError, AttributeError):
            return None

    @classmethod
    def resolve_import_or_raise(cls, reference: str) -> type:
        """Resolve a module/class reference, raising ModelOnexError on failure.

        This method is similar to resolve_import but raises a structured
        ModelOnexError instead of returning None when resolution fails.

        Args:
            reference: Fully qualified module.class path
                (e.g., 'omnibase_core.models.events.ModelEventEnvelope')

        Returns:
            The resolved class/type

        Raises:
            ModelOnexError: With IMPORT_ERROR or MODULE_NOT_FOUND error code
                if resolution fails

        Example:
            >>> ModelReference.resolve_import_or_raise('omnibase_core.models.events.ModelEventEnvelope')
            <class 'omnibase_core.models.events.ModelEventEnvelope'>
            >>> ModelReference.resolve_import_or_raise('invalid')  # doctest: +IGNORE_EXCEPTION_DETAIL
            Traceback (most recent call last):
                ...
            ModelOnexError: [ONEX_CORE_124_IMPORT_ERROR] Invalid reference format: 'invalid'
        """
        # Import here to avoid circular dependency
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        if not reference:
            raise ModelOnexError(
                message="Reference cannot be empty",
                error_code=EnumCoreErrorCode.IMPORT_ERROR,
                reference=reference,
            )

        if "." not in reference:
            raise ModelOnexError(
                message=f"Invalid reference format: '{reference}' (must be module.class)",
                error_code=EnumCoreErrorCode.IMPORT_ERROR,
                reference=reference,
            )

        module_path, class_name = reference.rsplit(".", 1)

        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ModelOnexError(
                message=f"Module not found: '{module_path}'",
                error_code=EnumCoreErrorCode.MODULE_NOT_FOUND,
                reference=reference,
                module_path=module_path,
                original_error=str(e),
            ) from e

        resolved_class: Any = getattr(module, class_name, None)
        if resolved_class is None:
            raise ModelOnexError(
                message=f"Class '{class_name}' not found in module '{module_path}'",
                error_code=EnumCoreErrorCode.IMPORT_ERROR,
                reference=reference,
                module_path=module_path,
                class_name=class_name,
            )

        return cast(type, resolved_class)

    def resolve(self) -> type | None:
        """Resolve this reference to its actual class/type.

        Uses the instance's module and class_name to resolve the reference.

        Returns:
            The resolved class/type, or None if resolution fails

        Example:
            >>> ref = ModelReference(
            ...     module="omnibase_core.models.events",
            ...     class_name="ModelEventEnvelope",
            ... )
            >>> ref.resolve()  # Returns the actual class
            <class 'omnibase_core.models.events.model_event_envelope.ModelEventEnvelope'>
        """
        return self.resolve_import(self.fully_qualified_name)

    def resolve_or_raise(self) -> type:
        """Resolve this reference to its actual class/type, raising on failure.

        Uses the instance's module and class_name to resolve the reference.
        Raises ModelOnexError if resolution fails.

        Returns:
            The resolved class/type

        Raises:
            ModelOnexError: With appropriate error code if resolution fails

        Example:
            >>> ref = ModelReference(
            ...     module="omnibase_core.models.events",
            ...     class_name="ModelEventEnvelope",
            ... )
            >>> ref.resolve_or_raise()  # Returns the actual class
            <class 'omnibase_core.models.events.model_event_envelope.ModelEventEnvelope'>
        """
        return self.resolve_import_or_raise(self.fully_qualified_name)

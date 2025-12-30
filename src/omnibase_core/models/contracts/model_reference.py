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
            "(e.g., 'omnibase_core.models.events')."
        ),
    )

    class_name: str = Field(
        ...,
        min_length=1,
        description=(
            "Name of the model class within the module (e.g., 'ModelEventEnvelope')."
        ),
    )

    version: str | None = Field(
        default=None,
        description="Optional version constraint for the model (e.g., '1.0.0').",
    )

    @field_validator("module")
    @classmethod
    def validate_module_format(cls, v: str) -> str:
        """Validate module path format."""
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
        """Validate class name format."""
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

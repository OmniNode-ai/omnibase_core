"""
ModelSecurityPolicyData: Security policy data container.

This model represents the serialized data structure for security policies.
Now uses strongly-typed values instead of Union types for better type safety.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.model.common.model_typed_value import (
    ModelTypedMapping,
    ModelValueContainer,
)


class ModelSecurityPolicyData(BaseModel):
    """Security policy data container with strong typing."""

    # Using ModelTypedMapping for type-safe policy data
    typed_data: ModelTypedMapping = Field(
        default_factory=ModelTypedMapping,
        description="Strongly-typed policy data fields",
    )

    # Backwards compatibility property
    @property
    def data(self) -> dict[str, str | int | float | bool | list | dict | None]:
        """Get policy data as a regular dictionary for backwards compatibility."""
        return self.typed_data.to_python_dict()

    def set_policy_value(
        self, key: str, value: str | int | float | bool | list | dict | None
    ) -> None:
        """
        Set a policy value with automatic type conversion.

        Args:
            key: Policy key
            value: Policy value (will be automatically typed)
        """
        self.typed_data.set_value(key, value)

    def get_policy_value(
        self, key: str, default: str | int | float | bool | list | dict | None = None
    ) -> str | int | float | bool | list | dict | None:
        """
        Get a policy value.

        Args:
            key: Policy key
            default: Default value if key not found

        Returns:
            The policy value or default
        """
        return self.typed_data.get_value(key, default)

    @classmethod
    def from_dict(
        cls, data: dict[str, str | int | float | bool | list | dict | None]
    ) -> "ModelSecurityPolicyData":
        """
        Create from a regular dictionary for backwards compatibility.

        Args:
            data: Dictionary of policy data

        Returns:
            ModelSecurityPolicyData with typed values
        """
        typed_mapping = ModelTypedMapping.from_python_dict(data)
        return cls(typed_data=typed_mapping)

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

from typing import Any, Union, cast

from pydantic import BaseModel, Field

"""
ModelSecurityPolicyData: Security policy data container.

This model represents the serialized data structure for security policies.
Now uses strongly-typed values instead of Union types for better type safety.
"""

from omnibase_core.models.common.model_typed_value import (
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

    # Current standards property
    @property
    def data(
        self,
    ) -> dict[str, str | int | float | bool | list[Any] | dict[str, Any] | None]:
        """Get policy data as a regular dictionary for current standards."""
        return cast(
            dict[str, str | int | float | bool | list[Any] | dict[str, Any] | None],
            self.typed_data.to_python_dict(),
        )

    def set_policy_value(
        self,
        key: str,
        value: str | int | float | bool | list[Any] | dict[str, Any] | None,
    ) -> None:
        """
        Set a policy value with automatic type conversion.

        Args:
            key: Policy key
            value: Policy value (will be automatically typed)
        """
        self.typed_data.set_value(key, value)

    def get_policy_value(
        self,
        key: str,
        default: str | int | float | bool | list[Any] | dict[str, Any] | None = None,
    ) -> str | int | float | bool | list[Any] | dict[str, Any] | None:
        """
        Get a policy value.

        Args:
            key: Policy key
            default: Default value if key not found

        Returns:
            The policy value or default
        """

        return cast(
            str | int | float | bool | list[Any] | dict[str, Any] | None,
            self.typed_data.get_value(key, default),
        )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, str | int | float | bool | list[Any] | dict[str, Any] | None],
    ) -> "ModelSecurityPolicyData":
        """
        Create from a regular dictionary using ONEX-compliant patterns.

        Args:
            data: Dictionary of policy data

        Returns:
            ModelSecurityPolicyData with typed values
        """
        # ONEX-compliant approach: Create empty mapping and populate through methods
        typed_mapping = ModelTypedMapping()
        for key, value in data.items():
            typed_mapping.set_value(key, value)
        return cls(typed_data=typed_mapping)

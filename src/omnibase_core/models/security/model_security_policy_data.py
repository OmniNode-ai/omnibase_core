"""
ModelSecurityPolicyData: Security policy data container.

This model represents the serialized data structure for security policies.
Now uses strongly-typed values instead of Union types for better type safety.
"""

from typing import cast

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_typed_value import ModelTypedMapping
from omnibase_core.types.type_json import JsonType


class ModelSecurityPolicyData(BaseModel):
    """Security policy data container with strong typing."""

    # Using ModelTypedMapping for type-safe policy data
    typed_data: ModelTypedMapping = Field(
        default_factory=ModelTypedMapping,
        description="Strongly-typed policy data fields",
    )

    # Current standards property
    @property
    def data(self) -> dict[str, JsonType]:
        """Get policy data as a regular dictionary for current standards."""
        return cast(
            "dict[str, JsonType]",
            self.typed_data.to_python_dict(),
        )

    def set_policy_value(
        self,
        key: str,
        value: JsonType,
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
        default: JsonType = None,
    ) -> JsonType:
        """
        Get a policy value.

        Args:
            key: Policy key
            default: Default value if key not found

        Returns:
            The policy value or default
        """

        return cast(
            JsonType,
            self.typed_data.get_value(key, default),
        )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, JsonType],
    ) -> "ModelSecurityPolicyData":
        """
        Create from a regular dictionary using ONEX-compatible patterns.

        Args:
            data: Dictionary of policy data

        Returns:
            ModelSecurityPolicyData with typed values
        """
        # ONEX-compatible approach: Create empty mapping and populate through methods
        typed_mapping = ModelTypedMapping()
        for key, value in data.items():
            typed_mapping.set_value(key, value)
        return cls(typed_data=typed_mapping)

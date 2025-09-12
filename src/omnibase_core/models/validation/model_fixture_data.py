"""
Canonical model for fixture data used in test and protocol infrastructure.
Decoupled from fixture/protocol modules to avoid circular imports.
Now uses strongly-typed value models instead of generic Union types.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_typed_value import (
    DictContainer,
    ListContainer,
    ModelValueContainer,
)


class ModelFixtureData(BaseModel):
    """
    Strongly typed model for a loaded fixture with proper type safety.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="Fixture name.")
    typed_data: ModelValueContainer = Field(
        ...,
        description="Strongly-typed fixture data with proper validation.",
    )

    @property
    def data(self) -> Any:
        """Get fixture data as Python value."""
        if hasattr(self.typed_data, "value"):
            return self.typed_data.value
        return None

    @property
    def is_dict_fixture(self) -> bool:
        """Check if this fixture contains dictionary data."""
        return isinstance(self.typed_data, DictContainer)

    @property
    def is_list_fixture(self) -> bool:
        """Check if this fixture contains list data."""
        return isinstance(self.typed_data, ListContainer)

    @property
    def is_primitive_fixture(self) -> bool:
        """Check if this fixture contains primitive data."""
        from omnibase_core.models.common.model_typed_value import ModelValueContainer

        return isinstance(self.typed_data, ModelValueContainer) and isinstance(
            self.typed_data.value,
            (str, int, float, bool, type(None)),
        )

    @classmethod
    def from_raw_data(cls, name: str, data: Any) -> "ModelFixtureData":
        """
        Create a fixture from raw Python data.

        Args:
            name: Fixture name
            data: Raw Python data

        Returns:
            ModelFixtureData with typed value
        """
        container = ModelValueContainer(value=data)
        return cls(name=name, typed_data=container)

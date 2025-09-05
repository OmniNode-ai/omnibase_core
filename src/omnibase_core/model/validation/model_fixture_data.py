"""
Canonical model for fixture data used in test and protocol infrastructure.
Decoupled from fixture/protocol modules to avoid circular imports.
"""

from typing import Any, Dict, List, Union
from pydantic import BaseModel, Field, ConfigDict


# Strongly typed union for fixture data types
FixtureDataType = Union[
    Dict[str, Any],  # Dictionary fixtures (most common)
    List[Any],       # List fixtures
    str,            # String fixtures
    int,            # Integer fixtures
    float,          # Float fixtures
    bool,           # Boolean fixtures
    None            # Null fixtures
]


class ModelFixtureData(BaseModel):
    """
    Strongly typed model for a loaded fixture with better type constraints.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="Fixture name.")
    data: FixtureDataType = Field(
        ...,
        description="Fixture data with constrained types (dict, list, or primitives).",
    )

    @property
    def is_dict_fixture(self) -> bool:
        """Check if this fixture contains dictionary data."""
        return isinstance(self.data, dict)

    @property
    def is_list_fixture(self) -> bool:
        """Check if this fixture contains list data."""
        return isinstance(self.data, list)

    @property
    def is_primitive_fixture(self) -> bool:
        """Check if this fixture contains primitive data."""
        return isinstance(self.data, (str, int, float, bool, type(None)))



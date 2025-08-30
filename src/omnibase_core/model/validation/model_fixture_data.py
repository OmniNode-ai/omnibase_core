"""
Canonical model for fixture data used in test and protocol infrastructure.
Decoupled from fixture/protocol modules to avoid circular imports.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelFixtureData(BaseModel):
    """
    Strongly typed model for a loaded fixture.
    """

    name: str = Field(..., description="Fixture name.")
    data: Any = Field(
        ...,
        description="Fixture data (arbitrary type, typically dict or list).",
    )


# Backward compatibility alias
FixtureDataModel = ModelFixtureData

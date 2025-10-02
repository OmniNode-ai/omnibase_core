"""Contract definitions model for ContractLoader."""

from typing import Any

from pydantic import BaseModel, Field


class ModelContractDefinitions(BaseModel):
    """Contract definitions section (optional)."""

    definitions: dict[str, Any] = Field(
        default_factory=dict, description="Schema definitions"
    )

    model_config = {
        "extra": "allow",
    }

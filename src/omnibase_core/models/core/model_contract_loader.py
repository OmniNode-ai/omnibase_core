"""Contract loader state model for ContractLoader."""

from pathlib import Path

from pydantic import BaseModel, Field


class ModelContractLoader(BaseModel):
    """State container for ContractLoader."""

    cache_enabled: bool = Field(default=True, description="Whether caching is enabled")
    base_path: Path = Field(description="Base path for contract resolution")
    loaded_contracts: dict[str, "ModelContractContent"] = Field(
        default_factory=dict,
        description="Cache of loaded contracts",
    )
    contract_cache: dict[str, "ModelContractCache"] = Field(
        default_factory=dict,
        description="File-level cache",
    )
    resolution_stack: list[str] = Field(
        default_factory=list,
        description="Stack for circular reference detection",
    )

    model_config = {
        "arbitrary_types_allowed": True,
    }


# Import here to avoid circular dependency
from omnibase_core.models.core.model_contract_cache import ModelContractCache
from omnibase_core.models.core.model_contract_content import ModelContractContent

ModelContractLoader.model_rebuild()

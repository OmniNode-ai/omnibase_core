"""Contract dependency model - alias to ModelDependency."""

# Alias ModelContractDependency to ModelDependency for contract loader compatibility
from omnibase_core.models.contracts.model_dependency import (
    ModelDependency as ModelContractDependency,
)

__all__ = ["ModelContractDependency"]

"""
ONEX Contracts Module.

This module provides:
1. Meta-models and contract definitions that all declarative node contracts
   must adhere to, ensuring cross-node consistency in the ONEX 4-node architecture.
2. Deterministic SHA256 fingerprinting for ONEX contracts, enabling drift
   detection between declarative and legacy versions during migration.

See: CONTRACT_STABILITY_SPEC.md for detailed specification.

VERSION: 1.0.0 - Meta-model definition added

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed
- Breaking changes require major version bump
"""

from omnibase_core.contracts.hash_registry import (
    ContractData,
    ContractHashRegistry,
    compute_contract_fingerprint,
    normalize_contract,
)

# Import models from their proper locations in models/contracts/
from omnibase_core.models.contracts.model_contract_fingerprint import (
    ModelContractFingerprint,
)
from omnibase_core.models.contracts.model_contract_meta import (
    ModelContractMeta,
    is_valid_meta_model,
    validate_meta_model,
)
from omnibase_core.models.contracts.model_contract_node_metadata import (
    ModelContractNodeMetadata,
)
from omnibase_core.models.contracts.model_contract_normalization_config import (
    ModelContractNormalizationConfig,
)
from omnibase_core.models.contracts.model_drift_result import (
    ModelDriftDetails,
    ModelDriftResult,
)
from omnibase_core.models.contracts.model_node_extensions import (
    ModelNodeExtensions,
)

__all__ = [
    # Hash Registry
    "ContractData",
    "ContractHashRegistry",
    "ModelContractFingerprint",
    "ModelContractNormalizationConfig",
    "ModelDriftDetails",
    "ModelDriftResult",
    "compute_contract_fingerprint",
    "normalize_contract",
    # Contract Meta Model
    "ModelContractNodeMetadata",
    "ModelNodeExtensions",
    "ModelContractMeta",
    "is_valid_meta_model",
    "validate_meta_model",
]

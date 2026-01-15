"""ONEX Contracts Module.

This module provides the contract infrastructure for the ONEX 4-node architecture:

1. **Contract Fingerprinting**: Deterministic SHA256 fingerprinting for ONEX contracts,
   enabling drift detection between declarative and legacy versions during migration.

2. **Meta-Models**: Contract definitions that all declarative node contracts must
   adhere to, ensuring cross-node consistency in the ONEX architecture.

3. **Drift Detection**: Tools for detecting when contracts have changed from their
   registered fingerprints, supporting safe migration workflows.

Exports:
    ContractHashRegistry: Registry for storing and retrieving contract fingerprints.
    ModelContractFingerprint: Pydantic model for contract fingerprints.
    ModelContractMeta: Meta-model for contract validation.
    ModelContractNodeMetadata: Node metadata contract model.
    ModelContractNormalizationConfig: Configuration for contract normalization.
    ModelDriftDetails: Detailed drift information.
    ModelDriftResult: Result of drift detection.
    ModelNodeExtensions: Extension points for nodes.
    compute_contract_fingerprint: Compute SHA256 fingerprint for a contract model.
    normalize_contract: Normalize contract model for deterministic hashing.
    is_valid_meta_model: Check if a model is a valid meta-model.
    validate_meta_model: Validate a model against meta-model requirements.
    IncludeLoader: YAML loader with !include directive support.
    load_contract: Load contract YAML with !include support.
    DEFAULT_MAX_INCLUDE_DEPTH: Default maximum include nesting depth (10).
    DEFAULT_MAX_FILE_SIZE: Default maximum file size (1MB).

Example:
    Basic fingerprinting workflow::

        from omnibase_core.contracts import (
            ContractHashRegistry,
            compute_contract_fingerprint,
        )
        from omnibase_core.models.contracts import ModelContractCompute

        # Compute fingerprint for a contract model
        contract = ModelContractCompute(name="my_node", version="0.4.0", ...)
        fingerprint = compute_contract_fingerprint(contract)
        print(fingerprint)  # Output: 0.4.0:8fa1e2b4c9d1

        # Register and detect drift
        registry = ContractHashRegistry()
        registry.register("my_node", fingerprint)
        drift_result = registry.detect_drift_from_contract("my_node", contract)
        print(drift_result.has_drift)  # Output: False

See Also:
    CONTRACT_STABILITY_SPEC.md: Detailed specification for contract stability.
    docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md: ONEX architecture overview.
    docs/guides/THREADING.md: Thread safety patterns for registry usage.

Thread Safety:
    ContractHashRegistry is NOT thread-safe. Use external synchronization
    (e.g., threading.Lock) if accessing from multiple threads.
    See docs/guides/THREADING.md for detailed thread safety patterns.

ONEX Compliance:
    This module is part of the ONEX contract infrastructure, ensuring:
    - Deterministic fingerprinting for change detection
    - Schema stability through meta-model validation
    - Migration safety between legacy and declarative implementations

Version:
    1.0.0 - Meta-model definition added

Stability Guarantee:
    - All fields, methods, and validators are stable interfaces
    - New optional fields may be added in minor versions only
    - Existing fields cannot be removed or have types/constraints changed
    - Breaking changes require major version bump
"""

from omnibase_core.contracts.contract_hash_registry import (
    ContractHashRegistry,
    compute_contract_fingerprint,
    normalize_contract,
)
from omnibase_core.contracts.contract_loader import (
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_MAX_INCLUDE_DEPTH,
    IncludeLoader,
    load_contract,
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
from omnibase_core.models.contracts.model_drift_details import ModelDriftDetails
from omnibase_core.models.contracts.model_drift_result import (
    DriftType,
    ModelDriftResult,
)
from omnibase_core.models.contracts.model_node_extensions import ModelNodeExtensions

__all__ = [
    # Hash Registry
    "ContractHashRegistry",
    "ModelContractFingerprint",
    "ModelContractNormalizationConfig",
    "DriftType",
    "ModelDriftDetails",
    "ModelDriftResult",
    "compute_contract_fingerprint",
    "normalize_contract",
    # Contract Loader (with !include support)
    "IncludeLoader",
    "load_contract",
    "DEFAULT_MAX_INCLUDE_DEPTH",
    "DEFAULT_MAX_FILE_SIZE",
    # Contract Meta Model
    "ModelContractNodeMetadata",
    "ModelNodeExtensions",
    "ModelContractMeta",
    "is_valid_meta_model",
    "validate_meta_model",
]

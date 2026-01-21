"""Contract Hash Registry.

This module provides deterministic SHA256 fingerprinting for ONEX contracts,
enabling drift detection between declarative and legacy versions during migration.

Features:
    - **Normalization Pipeline**: Defaults resolution, null removal, canonical ordering
    - **Fingerprint Format**: `<semver>:<sha256-first-12-hex-chars>` (e.g., `0.4.0:8fa1e2b4c9d1`)
    - **Registry**: Store and retrieve contract fingerprints by name
    - **Drift Detection**: Compare computed fingerprints against registered baselines

Example:
    Basic usage::

        from omnibase_core.contracts.contract_hash_registry import (
            ContractHashRegistry,
            compute_contract_fingerprint,
            normalize_contract,
        )

        # Normalize and fingerprint a contract
        contract = {"name": "my_node", "version": "0.4.0", "type": "compute"}
        normalized = normalize_contract(contract)
        fingerprint = compute_contract_fingerprint(contract)

        # Register and verify
        registry = ContractHashRegistry()
        registry.register("my_node", fingerprint)
        assert registry.verify("my_node", fingerprint)

See Also:
    CONTRACT_STABILITY_SPEC.md: Detailed specification for contract stability.
    docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md: ONEX 4-node architecture overview.
    docs/guides/THREADING.md: Thread safety patterns for production use.

ONEX Compliance:
    This module supports ONEX contract stability by providing deterministic
    fingerprinting that enables safe migration between legacy and declarative
    node implementations. All contracts in the ONEX ecosystem should be
    registered with a fingerprint for change tracking.

Stability Guarantee:
    - Fingerprint computation is deterministic across Python versions (3.10-3.12)
    - Same contract produces identical fingerprint before and after migration
    - Normalization is idempotent: ``normalize(normalize(c)) == normalize(c)``
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import VALIDATION_ERRORS
from omnibase_core.models.contracts.model_contract_fingerprint import (
    ModelContractFingerprint,
)
from omnibase_core.models.contracts.model_contract_normalization_config import (
    ModelContractNormalizationConfig,
)
from omnibase_core.models.contracts.model_contract_version import ModelContractVersion
from omnibase_core.models.contracts.model_drift_details import ModelDriftDetails
from omnibase_core.models.contracts.model_drift_result import (
    DriftType,
    ModelDriftResult,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


def _convert_to_json_serializable(value: object) -> object:
    """Convert non-JSON-serializable objects to JSON-compatible types.

    Args:
        value: Value to convert

    Returns:
        JSON-serializable representation of the value
    """
    if isinstance(value, ModelContractVersion):
        return str(value)
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {k: _convert_to_json_serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_convert_to_json_serializable(item) for item in value]
    return value


def _remove_nulls_recursive(data: dict[str, object]) -> dict[str, object]:
    """Recursively remove None/null values from a dictionary.

    Args:
        data: Dictionary to process

    Returns:
        New dictionary with null values removed
    """
    result: dict[str, object] = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, dict):
            nested = _remove_nulls_recursive(value)
            if nested:  # Only add non-empty dicts
                result[key] = nested
        elif isinstance(value, list):
            # Process lists, removing None items and recursing into dicts
            processed_list: list[object] = []
            for item in value:
                if item is None:
                    continue
                if isinstance(item, dict):
                    nested = _remove_nulls_recursive(item)
                    if nested:
                        processed_list.append(nested)
                else:
                    processed_list.append(item)
            # Always include lists, even if empty (preserve empty arrays)
            result[key] = processed_list
        else:
            result[key] = value
    return result


def _canonical_order_recursive(data: dict[str, object]) -> dict[str, object]:
    """Recursively sort dictionary keys alphabetically.

    Args:
        data: Dictionary to process

    Returns:
        New dictionary with sorted keys at all levels
    """
    result: dict[str, object] = {}
    for key in sorted(data.keys()):
        value = data[key]
        if isinstance(value, dict):
            result[key] = _canonical_order_recursive(value)
        elif isinstance(value, list):
            # Process lists, sorting dicts within them
            processed_list: list[object] = []
            for item in value:
                if isinstance(item, dict):
                    processed_list.append(_canonical_order_recursive(item))
                else:
                    processed_list.append(item)
            result[key] = processed_list
        else:
            result[key] = value
    return result


def normalize_contract(
    contract: BaseModel,
    config: ModelContractNormalizationConfig | None = None,
) -> str:
    """Normalize a contract model for deterministic fingerprinting.

    Applies the normalization pipeline from CONTRACT_STABILITY_SPEC.md:
    1. Remove null values (optional)
    2. Canonical key ordering (optional)
    3. Stable JSON serialization

    Args:
        contract: Pydantic contract model (e.g., ModelContractCompute, ModelContractEffect)
        config: Optional normalization configuration

    Returns:
        Normalized JSON string ready for hashing

    Raises:
        ModelOnexError: If contract cannot be normalized
    """
    if config is None:
        config = ModelContractNormalizationConfig()

    try:
        # Convert Pydantic model to dict
        normalized = contract.model_dump()

        # Step 0: Convert non-JSON-serializable objects (e.g., Pydantic models)
        converted = _convert_to_json_serializable(normalized)
        if not isinstance(converted, dict):
            raise ModelOnexError(
                message="Contract must be a dictionary",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                actual_type=type(converted).__name__,
                contract_type=type(contract).__name__,
            )
        normalized = converted

        # Step 1: Remove null values
        if config.remove_nulls:
            normalized = _remove_nulls_recursive(normalized)

        # Step 2: Canonical key ordering
        if config.sort_keys:
            normalized = _canonical_order_recursive(normalized)

        # Step 3: Stable JSON serialization
        if config.compact_json:
            return json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        else:
            return json.dumps(normalized, sort_keys=True, indent=2)

    except VALIDATION_ERRORS as e:
        raise ModelOnexError(
            message=f"Failed to normalize contract: {e}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            original_error=str(e),
            original_error_type=type(e).__name__,
            contract_type=type(contract).__name__,
        ) from e


def compute_contract_fingerprint(
    contract: BaseModel,
    config: ModelContractNormalizationConfig | None = None,
    include_normalized_content: bool = False,
) -> ModelContractFingerprint:
    """Compute a deterministic fingerprint for a contract.

    Fingerprint format: `<semver>:<sha256-first-12-hex-chars>`
    Example: `0.4.0:8fa1e2b4c9d1`

    Args:
        contract: Pydantic contract model (e.g., ModelContractCompute, ModelContractEffect)
        config: Optional normalization configuration
        include_normalized_content: If True, include normalized JSON in result

    Returns:
        ModelContractFingerprint with computed hash

    Raises:
        ModelOnexError: If contract cannot be fingerprinted

    Performance Characteristics:
        This function is intentionally stateless to support thread-safe usage.
        Typical performance on modern hardware:

        - Typical contract (~10-50 fields): <10ms
        - Large contract (~1000 fields): <100ms
        - Very large contract (~2000+ fields): <200ms

        The dominant factors are JSON serialization and normalization.
        SHA256 hashing is O(n) but typically negligible compared to
        JSON processing.
    """
    if config is None:
        config = ModelContractNormalizationConfig()

    # Extract version from contract (node contracts use contract_version)
    version_data = getattr(contract, "contract_version", None)
    if version_data is None:
        # Default to 0.0.0 if no version specified
        version = ModelContractVersion(major=0, minor=0, patch=0)
    elif isinstance(version_data, str):
        version = ModelContractVersion.from_string(version_data)
    elif isinstance(version_data, ModelContractVersion):
        version = version_data
    elif (
        # Duck-typing pattern (ONEX protocol standard) - accept any object with
        # major/minor/patch attributes rather than checking isinstance(). This
        # allows flexibility for different version types (ModelSemVer, etc.)
        hasattr(version_data, "major")
        and hasattr(version_data, "minor")
        and hasattr(version_data, "patch")
    ):
        version = ModelContractVersion(
            major=version_data.major,
            minor=version_data.minor,
            patch=version_data.patch,
        )
    else:
        raise ModelOnexError(
            message=f"Invalid version type in contract: {type(version_data).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            version_type=type(version_data).__name__,
            contract_type=type(contract).__name__,
            version_value=str(version_data)[:100],  # Truncate for safety
        )

    # Normalize the contract
    normalized = normalize_contract(contract, config)

    # Compute SHA256 hash
    hasher = hashlib.sha256(normalized.encode("utf-8"))
    full_hash = hasher.hexdigest()
    hash_prefix = full_hash[: config.hash_length]

    return ModelContractFingerprint(
        version=version,
        hash_prefix=hash_prefix,
        full_hash=full_hash,
        normalized_content=normalized if include_normalized_content else None,
    )


class ContractHashRegistry:
    """Registry for storing and retrieving contract fingerprints.

    Stores deterministic SHA256 fingerprints for loaded contracts,
    enabling drift detection between declarative and legacy versions.

    This registry provides a central location to track contract versions
    and detect when contracts have changed unexpectedly. It supports
    both registration of known-good fingerprints and verification of
    computed fingerprints against registered baselines.

    Attributes:
        _registry: Internal dictionary mapping contract names to fingerprints.
        _created_at: Timestamp when the registry was created (UTC).

    Thread Safety:
        This class is NOT thread-safe. Use external synchronization
        (e.g., threading.Lock) if accessing from multiple threads.
        See docs/guides/THREADING.md for detailed thread safety patterns.

    Example:
        Basic registration and lookup::

            >>> registry = ContractHashRegistry()
            >>> registry.register("my_contract", fingerprint)
            >>> registry.lookup("my_contract")
            ModelContractFingerprint(version='0.4.0', hash_prefix='8fa1e2b4c9d1')
            >>> registry.lookup_string("my_contract")
            '0.4.0:8fa1e2b4c9d1'

        Drift detection::

            >>> drift_result = registry.detect_drift("my_contract", computed_fingerprint)
            >>> drift_result.has_drift
            False

        Import/export::

            >>> exported = registry.to_dict()
            >>> new_registry = ContractHashRegistry.from_dict(exported)
    """

    def __init__(self) -> None:
        """Initialize an empty contract hash registry."""
        self._registry: dict[str, ModelContractFingerprint] = {}
        self._created_at: datetime = datetime.now(UTC)

    def register(
        self,
        contract_name: str,
        fingerprint: ModelContractFingerprint | str,
    ) -> None:
        """Register a contract fingerprint.

        Args:
            contract_name: Unique identifier for the contract (human-readable name)
            fingerprint: Fingerprint to register (object or string)

        Raises:
            ModelOnexError: If fingerprint is invalid
        """
        if not contract_name:
            raise ModelOnexError(
                message="Contract ID cannot be empty",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                provided_value=repr(contract_name),
            )

        if isinstance(fingerprint, str):
            fingerprint = ModelContractFingerprint.from_string(fingerprint)

        self._registry[contract_name] = fingerprint

    def register_from_contract(
        self,
        contract_name: str,
        contract: BaseModel,
        config: ModelContractNormalizationConfig | None = None,
    ) -> ModelContractFingerprint:
        """Compute and register a fingerprint from a contract model.

        Convenience method that computes the fingerprint and registers it.

        Args:
            contract_name: Unique identifier for the contract
            contract: Pydantic contract model to fingerprint
            config: Optional normalization configuration

        Returns:
            The computed and registered fingerprint
        """
        fingerprint = compute_contract_fingerprint(contract, config)
        self.register(contract_name, fingerprint)
        return fingerprint

    def lookup(self, contract_name: str) -> ModelContractFingerprint | None:
        """Look up a contract fingerprint.

        Args:
            contract_name: Unique identifier for the contract

        Returns:
            Registered fingerprint or None if not found
        """
        return self._registry.get(contract_name)

    def lookup_string(self, contract_name: str) -> str | None:
        """Look up a contract fingerprint as a string.

        Args:
            contract_name: Unique identifier for the contract

        Returns:
            Fingerprint string (e.g., '0.4.0:8fa1e2b4c9d1') or None
        """
        fingerprint = self.lookup(contract_name)
        return str(fingerprint) if fingerprint else None

    def verify(
        self,
        contract_name: str,
        expected: ModelContractFingerprint | str,
    ) -> bool:
        """Verify a contract matches expected fingerprint.

        Args:
            contract_name: Unique identifier for the contract
            expected: Expected fingerprint to verify against

        Returns:
            True if contract fingerprint matches expected, False otherwise
        """
        registered = self.lookup(contract_name)
        if registered is None:
            return False

        if isinstance(expected, str):
            expected = ModelContractFingerprint.from_string(expected)

        return registered.matches(expected)

    def detect_drift(
        self,
        contract_name: str,
        computed: ModelContractFingerprint | str,
    ) -> ModelDriftResult:
        """Detect if contract has drifted from registered fingerprint.

        Args:
            contract_name: Unique identifier for the contract
            computed: Computed fingerprint from current contract

        Returns:
            ModelDriftResult with drift detection details
        """
        if isinstance(computed, str):
            computed = ModelContractFingerprint.from_string(computed)

        registered = self.lookup(contract_name)

        if registered is None:
            return ModelDriftResult(
                contract_name=contract_name,
                has_drift=True,
                expected_fingerprint=None,
                computed_fingerprint=computed,
                drift_type="not_registered",
                details=ModelDriftDetails(reason="Contract not found in registry"),
            )

        # Check for drift
        version_match = registered.version == computed.version
        hash_match = registered.hash_prefix == computed.hash_prefix

        if version_match and hash_match:
            return ModelDriftResult(
                contract_name=contract_name,
                has_drift=False,
                expected_fingerprint=registered,
                computed_fingerprint=computed,
                drift_type=None,
            )

        # Determine drift type
        drift_type: DriftType
        if not version_match and not hash_match:
            drift_type = "both"
        elif not version_match:
            drift_type = "version"
        else:
            drift_type = "content"

        return ModelDriftResult(
            contract_name=contract_name,
            has_drift=True,
            expected_fingerprint=registered,
            computed_fingerprint=computed,
            drift_type=drift_type,
            details=ModelDriftDetails(
                version_match=version_match,
                hash_match=hash_match,
                expected_semver=str(registered.version),
                computed_semver=str(computed.version),
                expected_hash=registered.hash_prefix,
                computed_hash=computed.hash_prefix,
            ),
        )

    def detect_drift_from_contract(
        self,
        contract_name: str,
        contract: BaseModel,
        config: ModelContractNormalizationConfig | None = None,
    ) -> ModelDriftResult:
        """Detect drift by computing fingerprint from contract model.

        Convenience method that computes fingerprint before drift detection.

        Args:
            contract_name: Unique identifier for the contract
            contract: Pydantic contract model to check for drift
            config: Optional normalization configuration

        Returns:
            ModelDriftResult with drift detection details
        """
        computed = compute_contract_fingerprint(contract, config)
        return self.detect_drift(contract_name, computed)

    def unregister(self, contract_name: str) -> bool:
        """Remove a contract from the registry.

        Args:
            contract_name: Unique identifier for the contract

        Returns:
            True if contract was removed, False if not found
        """
        if contract_name in self._registry:
            del self._registry[contract_name]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries from the registry."""
        self._registry.clear()

    def list_contracts(self) -> list[str]:
        """List all registered contract IDs.

        Returns:
            List of contract IDs in registration order
        """
        return list(self._registry.keys())

    def count(self) -> int:
        """Get the number of registered contracts.

        Returns:
            Number of contracts in the registry
        """
        return len(self._registry)

    def to_dict(self) -> dict[str, str]:
        """Export registry as a dictionary of fingerprint strings.

        Returns:
            Dictionary mapping contract IDs to fingerprint strings
        """
        return {contract_name: str(fp) for contract_name, fp in self._registry.items()}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> ContractHashRegistry:
        """Create a registry from a dictionary of fingerprint strings.

        Args:
            data: Dictionary mapping contract IDs to fingerprint strings

        Returns:
            New ContractHashRegistry with imported fingerprints
        """
        registry = cls()
        for contract_name, fingerprint_str in data.items():
            registry.register(contract_name, fingerprint_str)
        return registry

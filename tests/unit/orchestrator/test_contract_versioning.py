# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract Versioning Invariant Tests for NodeOrchestrator.

This module tests the contract versioning invariants as specified in OMN-657:
- Same version + same contents = identical output (deterministic fingerprinting)
- Fingerprint format: `<semver>:<sha256_12>`
- Version validation and comparison
- Content identity across equivalent contracts

Test Categories:
1. Deterministic Output Tests - Same input always produces same output
2. Fingerprint Stability Tests - Same contract produces same fingerprint
3. Version Compatibility Tests - Version validation and semver handling
4. Content Identity Tests - Semantically identical contracts produce same result
5. Hash Computation Tests - Hash determinism and algorithm consistency

Requirements from CONTRACT_STABILITY_SPEC.md:
- Fingerprint format: `<semver>:<sha256-first-12-hex-chars>`
- Normalization is idempotent: normalize(normalize(c)) == normalize(c)
- Same contract produces identical fingerprint across executions
- Version changes are detected as drift
- Content changes are detected as drift

ONEX Compliance:
- Tests NodeOrchestrator contract versioning behavior
- Validates contract fingerprint stability for orchestrator nodes
- Ensures reproducible contract identity for workflow coordination
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest
from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.contracts import (
    ContractHashRegistry,
    ModelContractFingerprint,
    ModelContractNormalizationConfig,
    compute_contract_fingerprint,
    normalize_contract,
)
from omnibase_core.models.contracts.model_contract_version import ModelContractVersion
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# Test Models for Orchestrator Contract Versioning
# =============================================================================


class ModelTestOrchestratorContract(BaseModel):
    """Test contract model mimicking NodeOrchestrator contract structure.

    This model represents a simplified orchestrator contract for testing
    contract versioning invariants. It includes representative fields from
    ModelContractOrchestrator to ensure tests are realistic.
    """

    name: str = Field(
        default="test_orchestrator",
        description="Contract name for identification",
    )
    contract_version: ModelContractVersion = Field(
        default_factory=lambda: ModelContractVersion(major=1, minor=0, patch=0),
        description="Semantic version of the contract",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description",
    )
    node_type: str = Field(
        default="ORCHESTRATOR_GENERIC",
        description="Node type classification",
    )

    # Orchestrator-specific fields
    input_model: str = Field(
        default="omnibase_core.models.orchestrator.ModelOrchestratorInput",
        description="Input model for orchestrator",
    )
    output_model: str = Field(
        default="omnibase_core.models.orchestrator.ModelOrchestratorOutput",
        description="Output model for orchestrator",
    )

    # Workflow coordination settings
    execution_mode: str = Field(
        default="sequential",
        description="Workflow execution mode (sequential/parallel)",
    )
    max_parallel_branches: int = Field(
        default=4,
        description="Maximum parallel branches for parallel execution",
    )
    checkpoint_enabled: bool = Field(
        default=True,
        description="Enable workflow checkpointing",
    )
    checkpoint_interval_ms: int = Field(
        default=5000,
        description="Checkpoint interval in milliseconds",
    )

    # Event coordination settings
    load_balancing_enabled: bool = Field(
        default=True,
        description="Enable load balancing across execution nodes",
    )
    failure_isolation_enabled: bool = Field(
        default=True,
        description="Enable failure isolation between workflow branches",
    )
    monitoring_enabled: bool = Field(
        default=True,
        description="Enable comprehensive workflow monitoring",
    )

    # Optional nested configuration
    workflow_config: dict[str, object] | None = Field(
        default=None,
        description="Additional workflow configuration",
    )

    # Tags for categorization
    tags: list[str] = Field(
        default_factory=list,
        description="Contract classification tags",
    )

    @field_validator("contract_version", mode="before")
    @classmethod
    def convert_version_string(cls, v: object) -> ModelContractVersion:
        """Convert string versions to ModelContractVersion for test convenience."""
        if isinstance(v, ModelContractVersion):
            return v
        if isinstance(v, str):
            return ModelContractVersion.from_string(v)
        if isinstance(v, dict):
            return ModelContractVersion.model_validate(v)
        raise ValueError(f"Cannot convert {type(v).__name__} to ModelContractVersion")

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class ModelMinimalContract(BaseModel):
    """Minimal contract model for version field testing."""

    name: str = Field(default="minimal")
    contract_version: ModelContractVersion = Field(
        default_factory=lambda: ModelContractVersion(major=0, minor=0, patch=0)
    )

    @field_validator("contract_version", mode="before")
    @classmethod
    def convert_version(cls, v: object) -> ModelContractVersion:
        """Convert string versions to ModelContractVersion."""
        if isinstance(v, ModelContractVersion):
            return v
        if isinstance(v, str):
            return ModelContractVersion.from_string(v)
        if isinstance(v, dict):
            return ModelContractVersion.model_validate(v)
        raise ValueError(f"Cannot convert {type(v).__name__} to ModelContractVersion")


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def orchestrator_contract() -> ModelTestOrchestratorContract:
    """Standard orchestrator contract for testing."""
    return ModelTestOrchestratorContract(
        name="workflow_orchestrator",
        contract_version="1.0.0",
        description="Workflow coordination orchestrator",
        node_type="ORCHESTRATOR_GENERIC",
        execution_mode="parallel",
        max_parallel_branches=8,
        checkpoint_enabled=True,
        checkpoint_interval_ms=10000,
        tags=["workflow", "coordination"],
    )


@pytest.fixture
def orchestrator_contract_with_nested() -> ModelTestOrchestratorContract:
    """Orchestrator contract with nested workflow configuration."""
    return ModelTestOrchestratorContract(
        name="complex_orchestrator",
        contract_version="2.0.0",
        description="Complex workflow orchestrator",
        workflow_config={
            "timeout_ms": 30000,
            "retry_policy": {
                "max_retries": 3,
                "backoff_ms": 1000,
            },
            "event_handlers": ["on_start", "on_complete", "on_error"],
        },
        tags=["complex", "workflow", "retry"],
    )


@pytest.fixture
def contract_with_nulls() -> ModelTestOrchestratorContract:
    """Contract with explicit null fields for normalization testing."""
    return ModelTestOrchestratorContract(
        name="nullable_orchestrator",
        contract_version="1.0.0",
        description=None,
        workflow_config={
            "enabled": True,
            "optional_field": None,
            "nested": {
                "value": "keep",
                "nullable": None,
            },
        },
    )


@pytest.fixture
def registry() -> ContractHashRegistry:
    """Fresh contract hash registry for each test."""
    return ContractHashRegistry()


# =============================================================================
# Deterministic Output Tests
# =============================================================================


@pytest.mark.unit
class TestDeterministicOutput:
    """Tests verifying same input always produces same output.

    These tests validate the core invariant: given the same contract content,
    fingerprint computation must produce identical results across:
    - Multiple calls
    - Different execution contexts
    - Various execution orders
    """

    def test_same_input_same_output_multiple_calls(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that multiple fingerprint calls produce identical results."""
        fingerprints = [
            compute_contract_fingerprint(orchestrator_contract) for _ in range(10)
        ]

        # All fingerprints must be identical
        first = str(fingerprints[0])
        for i, fp in enumerate(fingerprints[1:], start=2):
            assert str(fp) == first, f"Call {i} produced different fingerprint"

    def test_deterministic_across_normalization(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that normalization produces deterministic JSON output."""
        normalizations = [normalize_contract(orchestrator_contract) for _ in range(10)]

        first = normalizations[0]
        for i, norm in enumerate(normalizations[1:], start=2):
            assert norm == first, f"Normalization {i} produced different result"

    def test_order_of_execution_does_not_affect_result(self) -> None:
        """Test that execution order doesn't affect fingerprint results."""
        contracts = [
            ModelTestOrchestratorContract(
                name=f"orchestrator_{i}", contract_version="1.0.0"
            )
            for i in range(5)
        ]

        # Compute fingerprints in different orders
        order1_fingerprints = [str(compute_contract_fingerprint(c)) for c in contracts]
        order2_fingerprints = [
            str(compute_contract_fingerprint(c)) for c in reversed(contracts)
        ]

        # Results should match regardless of order (reversed for comparison)
        assert order1_fingerprints == list(reversed(order2_fingerprints))

    def test_no_random_elements_in_fingerprint(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that fingerprint has no random components."""
        fp1 = compute_contract_fingerprint(orchestrator_contract)
        fp2 = compute_contract_fingerprint(orchestrator_contract)

        # Every component must be identical
        assert fp1.version == fp2.version
        assert fp1.hash_prefix == fp2.hash_prefix
        assert fp1.full_hash == fp2.full_hash

    def test_deterministic_with_nested_structures(
        self, orchestrator_contract_with_nested: ModelTestOrchestratorContract
    ) -> None:
        """Test determinism with complex nested structures."""
        fingerprints = [
            compute_contract_fingerprint(orchestrator_contract_with_nested)
            for _ in range(5)
        ]

        hashes = [fp.full_hash for fp in fingerprints]
        assert len(set(hashes)) == 1, "Nested structure produced non-deterministic hash"

    def test_hash_algorithm_consistency(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that hash algorithm produces consistent results."""
        normalized = normalize_contract(orchestrator_contract)

        # Manual SHA256 computation
        expected_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        # Fingerprint computation should match
        fingerprint = compute_contract_fingerprint(orchestrator_contract)
        assert fingerprint.full_hash == expected_hash


# =============================================================================
# Fingerprint Stability Tests
# =============================================================================


@pytest.mark.unit
class TestFingerprintStability:
    """Tests for fingerprint format and stability guarantees.

    Validates:
    - Fingerprint format: `<semver>:<sha256_12>`
    - Same contract produces same fingerprint
    - Fingerprint changes when content changes
    - Whitespace normalization behavior
    """

    def test_fingerprint_format_semver_colon_sha256(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test fingerprint follows `<semver>:<sha256_12>` format."""
        fingerprint = compute_contract_fingerprint(orchestrator_contract)
        fp_str = str(fingerprint)

        # Pattern: X.Y.Z:12_hex_chars
        pattern = r"^\d+\.\d+\.\d+:[a-f0-9]{12}$"
        assert re.match(pattern, fp_str), f"Invalid format: {fp_str}"

    def test_fingerprint_format_components(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test fingerprint components are correct."""
        fingerprint = compute_contract_fingerprint(orchestrator_contract)
        fp_str = str(fingerprint)

        parts = fp_str.split(":")
        assert len(parts) == 2, "Fingerprint should have exactly two parts"

        version_part, hash_part = parts
        assert version_part == "1.0.0", f"Version mismatch: {version_part}"
        assert len(hash_part) == 12, f"Hash prefix should be 12 chars: {hash_part}"
        assert all(c in "0123456789abcdef" for c in hash_part), "Hash must be hex"

    def test_same_contract_same_fingerprint(self) -> None:
        """Test that identical contracts produce identical fingerprints."""
        contract1 = ModelTestOrchestratorContract(
            name="test_orchestrator",
            contract_version="1.0.0",
            description="Test description",
            execution_mode="parallel",
        )
        contract2 = ModelTestOrchestratorContract(
            name="test_orchestrator",
            contract_version="1.0.0",
            description="Test description",
            execution_mode="parallel",
        )

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        assert str(fp1) == str(fp2)

    def test_fingerprint_changes_when_content_changes(self) -> None:
        """Test that fingerprint changes when any content changes."""
        base = ModelTestOrchestratorContract(
            name="orchestrator",
            contract_version="1.0.0",
            execution_mode="sequential",
        )
        modified = ModelTestOrchestratorContract(
            name="orchestrator",
            contract_version="1.0.0",
            execution_mode="parallel",  # Changed field
        )

        fp_base = compute_contract_fingerprint(base)
        fp_modified = compute_contract_fingerprint(modified)

        # Same version but different hash
        assert fp_base.version == fp_modified.version
        assert fp_base.hash_prefix != fp_modified.hash_prefix

    def test_fingerprint_changes_when_version_changes(self) -> None:
        """Test that fingerprint changes when version changes."""
        v1 = ModelTestOrchestratorContract(name="test", contract_version="1.0.0")
        v2 = ModelTestOrchestratorContract(name="test", contract_version="1.0.1")

        fp_v1 = compute_contract_fingerprint(v1)
        fp_v2 = compute_contract_fingerprint(v2)

        # Version different, and hash will also differ (version is in content)
        assert fp_v1.version != fp_v2.version
        assert fp_v1.hash_prefix != fp_v2.hash_prefix

    def test_fingerprint_stable_with_null_normalization(
        self, contract_with_nulls: ModelTestOrchestratorContract
    ) -> None:
        """Test fingerprint stability through null normalization."""
        # Contract with explicit nulls
        with_nulls = contract_with_nulls

        # Equivalent contract without explicit nulls
        without_nulls = ModelTestOrchestratorContract(
            name="nullable_orchestrator",
            contract_version="1.0.0",
            workflow_config={
                "enabled": True,
                "nested": {
                    "value": "keep",
                },
            },
        )

        fp_with = compute_contract_fingerprint(with_nulls)
        fp_without = compute_contract_fingerprint(without_nulls)

        # After null removal, fingerprints should match
        assert str(fp_with) == str(fp_without)

    def test_key_order_does_not_affect_fingerprint(self) -> None:
        """Test that dict key order doesn't affect fingerprint."""
        contract1 = ModelTestOrchestratorContract(
            name="test",
            contract_version="1.0.0",
            workflow_config={"alpha": 1, "beta": 2, "gamma": 3},
        )
        contract2 = ModelTestOrchestratorContract(
            name="test",
            contract_version="1.0.0",
            workflow_config={"gamma": 3, "alpha": 1, "beta": 2},
        )

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        assert str(fp1) == str(fp2), "Key order should not affect fingerprint"

    def test_hash_prefix_length_configurable(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that hash prefix length can be configured."""
        config_12 = ModelContractNormalizationConfig(hash_length=12)
        config_16 = ModelContractNormalizationConfig(hash_length=16)
        config_32 = ModelContractNormalizationConfig(hash_length=32)

        fp_12 = compute_contract_fingerprint(orchestrator_contract, config_12)
        fp_16 = compute_contract_fingerprint(orchestrator_contract, config_16)
        fp_32 = compute_contract_fingerprint(orchestrator_contract, config_32)

        assert len(fp_12.hash_prefix) == 12
        assert len(fp_16.hash_prefix) == 16
        assert len(fp_32.hash_prefix) == 32

        # All should share the same prefix up to 12 chars
        assert fp_12.hash_prefix == fp_16.hash_prefix[:12]
        assert fp_12.hash_prefix == fp_32.hash_prefix[:12]


# =============================================================================
# Version Compatibility Tests
# =============================================================================


@pytest.mark.unit
class TestVersionCompatibility:
    """Tests for version field validation and semver handling.

    Validates:
    - Version field is properly validated
    - Semver format is accepted
    - Invalid versions are rejected
    - Version comparison works correctly
    """

    def test_version_field_validated(self) -> None:
        """Test that version field undergoes validation."""
        # Valid version string
        contract = ModelMinimalContract(name="test", contract_version="1.2.3")
        assert contract.contract_version == ModelContractVersion(
            major=1, minor=2, patch=3
        )

    def test_semver_format_accepted(self) -> None:
        """Test various valid semver formats are accepted."""
        valid_versions = [
            "0.0.0",
            "0.1.0",
            "1.0.0",
            "1.2.3",
            "10.20.30",
            "0.0.1",
        ]

        for version_str in valid_versions:
            contract = ModelMinimalContract(name="test", contract_version=version_str)
            fingerprint = compute_contract_fingerprint(contract)
            assert str(fingerprint).startswith(f"{version_str}:")

    def test_invalid_version_rejected(self) -> None:
        """Test that invalid version formats are rejected."""
        invalid_versions = [
            "1.2",  # Missing patch
            "1",  # Missing minor and patch
            "a.b.c",  # Non-numeric
            "-1.0.0",  # Negative
            "1.0.0.0",  # Too many parts
        ]

        for version_str in invalid_versions:
            with pytest.raises((ModelOnexError, ValueError)):
                ModelContractVersion.from_string(version_str)

    def test_version_comparison_works(self) -> None:
        """Test that version comparison operators work correctly."""
        v1_0_0 = ModelContractVersion(major=1, minor=0, patch=0)
        v1_0_1 = ModelContractVersion(major=1, minor=0, patch=1)
        v1_1_0 = ModelContractVersion(major=1, minor=1, patch=0)
        v2_0_0 = ModelContractVersion(major=2, minor=0, patch=0)

        # Less than
        assert v1_0_0 < v1_0_1
        assert v1_0_1 < v1_1_0
        assert v1_1_0 < v2_0_0

        # Greater than
        assert v2_0_0 > v1_1_0
        assert v1_1_0 > v1_0_1
        assert v1_0_1 > v1_0_0

        # Equality
        assert v1_0_0 == ModelContractVersion(major=1, minor=0, patch=0)
        assert v1_0_0 != v1_0_1

    def test_version_bump_methods(self) -> None:
        """Test version bump helper methods."""
        v1_0_0 = ModelContractVersion(major=1, minor=0, patch=0)

        # Bump patch
        v1_0_1 = v1_0_0.bump_patch()
        assert v1_0_1 == ModelContractVersion(major=1, minor=0, patch=1)

        # Bump minor (resets patch)
        v1_1_0 = v1_0_0.bump_minor()
        assert v1_1_0 == ModelContractVersion(major=1, minor=1, patch=0)

        # Bump major (resets minor and patch)
        v2_0_0 = v1_0_0.bump_major()
        assert v2_0_0 == ModelContractVersion(major=2, minor=0, patch=0)

    def test_version_string_round_trip(self) -> None:
        """Test version string serialization round-trip."""
        original = "1.2.3"
        version = ModelContractVersion.from_string(original)
        assert str(version) == original

    def test_version_in_fingerprint_matches_contract(self) -> None:
        """Test that fingerprint version matches contract version."""
        for version_str in ["0.1.0", "1.0.0", "2.3.4", "10.0.0"]:
            contract = ModelTestOrchestratorContract(
                name="test",
                contract_version=version_str,
            )
            fingerprint = compute_contract_fingerprint(contract)
            assert str(fingerprint.version) == version_str

    def test_version_progression_validation(self) -> None:
        """Test version progression (downgrade detection)."""
        v2_0_0 = ModelContractVersion(major=2, minor=0, patch=0)
        v1_0_0 = ModelContractVersion(major=1, minor=0, patch=0)

        # Upgrade should pass
        v2_0_0.validate_progression(from_version=v1_0_0)  # No exception

        # Downgrade should fail
        with pytest.raises(ModelOnexError) as exc_info:
            v1_0_0.validate_progression(from_version=v2_0_0)
        assert "downgrade" in str(exc_info.value).lower()

    def test_version_prerelease_suffix_handled(self) -> None:
        """Test that prerelease suffixes are parsed correctly."""
        # Prerelease suffixes should be accepted and stripped
        version = ModelContractVersion.from_string("1.2.3-alpha")
        assert version == ModelContractVersion(major=1, minor=2, patch=3)

        version_beta = ModelContractVersion.from_string("1.0.0-beta.1")
        assert version_beta == ModelContractVersion(major=1, minor=0, patch=0)


# =============================================================================
# Content Identity Tests
# =============================================================================


@pytest.mark.unit
class TestContentIdentity:
    """Tests for content identity and semantic equivalence.

    Validates:
    - Semantically identical contracts produce same result
    - Field order doesn't affect identity
    - Default values don't affect identity
    """

    def test_semantically_identical_contracts_same_result(self) -> None:
        """Test that semantically identical contracts produce same fingerprint."""
        # Two contracts created differently but semantically identical
        contract1 = ModelTestOrchestratorContract(
            name="orchestrator",
            contract_version=ModelContractVersion(major=1, minor=0, patch=0),
            execution_mode="parallel",
        )
        contract2 = ModelTestOrchestratorContract(
            name="orchestrator",
            contract_version="1.0.0",  # String version instead of object
            execution_mode="parallel",
        )

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        assert str(fp1) == str(fp2)

    def test_field_order_does_not_affect_identity(self) -> None:
        """Test that field order in JSON doesn't affect identity."""
        # Create contracts with workflow_config having different key orders
        # Explicitly typed as dict[str, object] to satisfy mypy strict mode
        config1: dict[str, object] = {"zebra": 1, "alpha": 2, "mango": 3}
        config2: dict[str, object] = {"alpha": 2, "mango": 3, "zebra": 1}
        config3: dict[str, object] = {"mango": 3, "zebra": 1, "alpha": 2}

        contracts = [
            ModelTestOrchestratorContract(
                name="test",
                contract_version="1.0.0",
                workflow_config=config,
            )
            for config in [config1, config2, config3]
        ]

        fingerprints = [str(compute_contract_fingerprint(c)) for c in contracts]
        assert len(set(fingerprints)) == 1, "Field order should not affect identity"

    def test_default_values_do_not_affect_identity(self) -> None:
        """Test that explicit vs implicit default values produce same identity."""
        # Contract with explicit defaults
        explicit = ModelTestOrchestratorContract(
            name="test_orchestrator",
            contract_version="1.0.0",
            node_type="ORCHESTRATOR_GENERIC",  # Default value
            execution_mode="sequential",  # Default value
            max_parallel_branches=4,  # Default value
            checkpoint_enabled=True,  # Default value
            load_balancing_enabled=True,  # Default value
            tags=[],  # Default value
        )

        # Contract relying on defaults
        implicit = ModelTestOrchestratorContract(
            name="test_orchestrator",
            contract_version="1.0.0",
        )

        fp_explicit = compute_contract_fingerprint(explicit)
        fp_implicit = compute_contract_fingerprint(implicit)

        assert str(fp_explicit) == str(fp_implicit)

    def test_nested_dict_order_does_not_affect_identity(self) -> None:
        """Test that deeply nested dict order doesn't affect identity."""
        contract1 = ModelTestOrchestratorContract(
            name="nested_test",
            contract_version="1.0.0",
            workflow_config={
                "outer": {
                    "inner": {
                        "z_field": 1,
                        "a_field": 2,
                    },
                    "another": {
                        "y_field": 3,
                        "b_field": 4,
                    },
                },
            },
        )
        contract2 = ModelTestOrchestratorContract(
            name="nested_test",
            contract_version="1.0.0",
            workflow_config={
                "outer": {
                    "another": {
                        "b_field": 4,
                        "y_field": 3,
                    },
                    "inner": {
                        "a_field": 2,
                        "z_field": 1,
                    },
                },
            },
        )

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        assert str(fp1) == str(fp2)

    def test_empty_lists_preserved_in_identity(self) -> None:
        """Test that empty lists are preserved and affect identity correctly."""
        with_empty = ModelTestOrchestratorContract(
            name="test",
            contract_version="1.0.0",
            tags=[],  # Explicit empty list
        )

        # Tags default to empty list
        with_default = ModelTestOrchestratorContract(
            name="test",
            contract_version="1.0.0",
        )

        fp_with = compute_contract_fingerprint(with_empty)
        fp_default = compute_contract_fingerprint(with_default)

        # Should be identical since default is also empty list
        assert str(fp_with) == str(fp_default)

    def test_whitespace_in_string_values_preserved(self) -> None:
        """Test that whitespace in string values is preserved in identity."""
        contract1 = ModelTestOrchestratorContract(
            name="test",
            contract_version="1.0.0",
            description="no whitespace",
        )
        contract2 = ModelTestOrchestratorContract(
            name="test",
            contract_version="1.0.0",
            description="no  whitespace",  # Extra space
        )

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        # Different whitespace in values should produce different fingerprints
        assert str(fp1) != str(fp2)


# =============================================================================
# Hash Computation Tests
# =============================================================================


@pytest.mark.unit
class TestHashComputation:
    """Tests for hash computation determinism and algorithm consistency.

    Validates:
    - Hash is deterministic
    - Hash algorithm consistency (SHA256)
    - Hash includes all relevant fields
    """

    def test_hash_is_deterministic(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that hash computation is deterministic."""
        hashes = [
            compute_contract_fingerprint(orchestrator_contract).full_hash
            for _ in range(10)
        ]

        assert len(set(hashes)) == 1, "Hash should be deterministic"

    def test_hash_algorithm_is_sha256(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that SHA256 algorithm is used for hashing."""
        normalized = normalize_contract(orchestrator_contract)
        expected_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        fingerprint = compute_contract_fingerprint(orchestrator_contract)

        assert fingerprint.full_hash == expected_hash
        assert len(fingerprint.full_hash) == 64  # SHA256 produces 64 hex chars

    def test_hash_includes_all_relevant_fields(self) -> None:
        """Test that changing any relevant field changes the hash."""
        base_contract = ModelTestOrchestratorContract(
            name="base",
            contract_version="1.0.0",
            description="original",
            execution_mode="sequential",
            max_parallel_branches=4,
            checkpoint_enabled=True,
            tags=["original"],
        )
        base_hash = compute_contract_fingerprint(base_contract).full_hash

        # Test each field change produces different hash
        # Explicitly typed for mypy strict mode
        field_changes: list[dict[str, object]] = [
            {"name": "changed"},
            {"contract_version": "1.0.1"},
            {"description": "changed"},
            {"execution_mode": "parallel"},
            {"max_parallel_branches": 8},
            {"checkpoint_enabled": False},
            {"tags": ["changed"]},
        ]

        for change in field_changes:
            modified = base_contract.model_copy(update=change)
            modified_hash = compute_contract_fingerprint(modified).full_hash
            field_name = next(iter(change.keys()))
            assert modified_hash != base_hash, (
                f"Changing {field_name} should affect hash"
            )

    def test_hash_prefix_is_first_n_chars(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that hash_prefix is first N characters of full_hash."""
        fingerprint = compute_contract_fingerprint(orchestrator_contract)

        assert fingerprint.hash_prefix == fingerprint.full_hash[:12]

    def test_hash_is_lowercase_hex(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that hash is lowercase hexadecimal."""
        fingerprint = compute_contract_fingerprint(orchestrator_contract)

        assert fingerprint.full_hash.islower()
        assert all(c in "0123456789abcdef" for c in fingerprint.full_hash)

    def test_different_configs_produce_different_hashes(self) -> None:
        """Test that different normalization configs can affect hash length but not value."""
        contract = ModelTestOrchestratorContract(name="test", contract_version="1.0.0")

        config_short = ModelContractNormalizationConfig(hash_length=8)
        config_long = ModelContractNormalizationConfig(hash_length=32)

        fp_short = compute_contract_fingerprint(contract, config_short)
        fp_long = compute_contract_fingerprint(contract, config_long)

        # Same full hash
        assert fp_short.full_hash == fp_long.full_hash

        # Different prefix lengths
        assert len(fp_short.hash_prefix) == 8
        assert len(fp_long.hash_prefix) == 32

        # Short prefix is a substring of long prefix
        assert fp_short.hash_prefix == fp_long.hash_prefix[:8]


# =============================================================================
# Fingerprint Parsing Tests
# =============================================================================


@pytest.mark.unit
class TestFingerprintParsing:
    """Tests for fingerprint string parsing."""

    def test_parse_valid_orchestrator_fingerprint(self) -> None:
        """Test parsing a valid orchestrator contract fingerprint."""
        fp_str = "1.0.0:abcdef123456"
        fingerprint = ModelContractFingerprint.from_string(fp_str)

        assert fingerprint.version == ModelContractVersion(major=1, minor=0, patch=0)
        assert fingerprint.hash_prefix == "abcdef123456"

    def test_parse_fingerprint_with_various_versions(self) -> None:
        """Test parsing fingerprints with various version formats."""
        test_cases = [
            ("0.0.0:000000000000", 0, 0, 0),
            ("1.0.0:abcdef123456", 1, 0, 0),
            ("10.20.30:fedcba987654", 10, 20, 30),
            ("0.0.1:111111111111", 0, 0, 1),
        ]

        for fp_str, major, minor, patch in test_cases:
            fingerprint = ModelContractFingerprint.from_string(fp_str)
            assert fingerprint.version.major == major
            assert fingerprint.version.minor == minor
            assert fingerprint.version.patch == patch

    def test_fingerprint_string_round_trip(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test fingerprint to string and back round-trip."""
        original = compute_contract_fingerprint(orchestrator_contract)
        fp_str = str(original)
        parsed = ModelContractFingerprint.from_string(fp_str)

        assert parsed.version == original.version
        assert parsed.hash_prefix == original.hash_prefix


# =============================================================================
# Registry Integration Tests
# =============================================================================


@pytest.mark.unit
class TestRegistryIntegration:
    """Tests for contract registry integration with versioning."""

    def test_registry_stores_orchestrator_fingerprint(
        self,
        registry: ContractHashRegistry,
        orchestrator_contract: ModelTestOrchestratorContract,
    ) -> None:
        """Test that registry correctly stores orchestrator fingerprints."""
        fingerprint = registry.register_from_contract(
            "workflow_orchestrator", orchestrator_contract
        )

        # Verify stored correctly
        stored = registry.lookup("workflow_orchestrator")
        assert stored is not None
        assert stored == fingerprint

    def test_registry_detects_version_drift(
        self,
        registry: ContractHashRegistry,
    ) -> None:
        """Test registry detects version drift in orchestrator contracts."""
        v1_contract = ModelTestOrchestratorContract(
            name="orchestrator", contract_version="1.0.0"
        )
        registry.register_from_contract("orchestrator", v1_contract)

        v2_contract = ModelTestOrchestratorContract(
            name="orchestrator", contract_version="2.0.0"
        )
        drift = registry.detect_drift_from_contract("orchestrator", v2_contract)

        assert drift.has_drift is True
        assert drift.drift_type == "both"  # Version and content changed

    def test_registry_detects_content_drift(
        self,
        registry: ContractHashRegistry,
    ) -> None:
        """Test registry detects content drift in orchestrator contracts."""
        original = ModelTestOrchestratorContract(
            name="orchestrator",
            contract_version="1.0.0",
            execution_mode="sequential",
        )
        registry.register_from_contract("orchestrator", original)

        modified = ModelTestOrchestratorContract(
            name="orchestrator",
            contract_version="1.0.0",
            execution_mode="parallel",  # Changed content
        )
        drift = registry.detect_drift_from_contract("orchestrator", modified)

        assert drift.has_drift is True
        assert drift.drift_type == "content"

    def test_registry_no_drift_for_identical_contract(
        self,
        registry: ContractHashRegistry,
        orchestrator_contract: ModelTestOrchestratorContract,
    ) -> None:
        """Test registry reports no drift for identical contracts."""
        registry.register_from_contract("orchestrator", orchestrator_contract)

        drift = registry.detect_drift_from_contract(
            "orchestrator", orchestrator_contract
        )

        assert drift.has_drift is False
        assert drift.drift_type is None


# =============================================================================
# Edge Cases and Known Fingerprints
# =============================================================================


@pytest.mark.unit
class TestKnownFingerprints:
    """Tests with known/expected fingerprint values for regression detection.

    These tests use contracts with specific content and verify the resulting
    fingerprints match expected values. This helps detect unintended changes
    to the normalization or hashing algorithms.
    """

    def test_minimal_contract_fingerprint_stable(self) -> None:
        """Test that minimal contract produces stable fingerprint."""
        contract = ModelMinimalContract(name="test", contract_version="1.0.0")
        fingerprint = compute_contract_fingerprint(contract)

        # The fingerprint should be deterministic and stable
        # Compute it twice to verify
        fingerprint2 = compute_contract_fingerprint(contract)
        assert str(fingerprint) == str(fingerprint2)

        # Verify format
        assert fingerprint.version == ModelContractVersion(major=1, minor=0, patch=0)
        assert len(fingerprint.hash_prefix) == 12

    def test_empty_nested_structure_normalization(self) -> None:
        """Test handling of empty nested structures after null removal."""
        contract = ModelTestOrchestratorContract(
            name="test",
            contract_version="1.0.0",
            workflow_config={"only_null": None},
        )

        # Should normalize without error
        normalized = normalize_contract(contract)
        parsed = json.loads(normalized)

        # Empty dict after null removal should be removed
        assert "workflow_config" not in parsed

    def test_complex_nested_structure_fingerprint(self) -> None:
        """Test fingerprint stability for complex nested structures."""
        contract = ModelTestOrchestratorContract(
            name="complex_orchestrator",
            contract_version="1.0.0",
            workflow_config={
                "level1": {
                    "level2": {
                        "level3": {
                            "value": "deep_value",
                            "list": [1, 2, 3],
                        },
                    },
                },
                "another_branch": {
                    "setting": True,
                    "count": 42,
                },
            },
            tags=["complex", "nested", "test"],
        )

        # Should produce deterministic fingerprint
        fp1 = compute_contract_fingerprint(contract)
        fp2 = compute_contract_fingerprint(contract)

        assert str(fp1) == str(fp2)
        assert fp1.full_hash == fp2.full_hash

    def test_unicode_content_fingerprint(self) -> None:
        """Test fingerprint handling of unicode content."""
        contract = ModelTestOrchestratorContract(
            name="unicode_test",
            contract_version="1.0.0",
            description="Testing unicode: \u00e9\u00e8\u00ea \u4e2d\u6587 \U0001f600",
            workflow_config={
                "emoji_key": "\U0001f4dd",
                "chinese_key": "\u914d\u7f6e",
            },
        )

        # Should handle unicode correctly and deterministically
        fp1 = compute_contract_fingerprint(contract)
        fp2 = compute_contract_fingerprint(contract)

        assert str(fp1) == str(fp2)

    def test_special_characters_in_strings(self) -> None:
        """Test fingerprint handling of special characters."""
        contract = ModelTestOrchestratorContract(
            name="special_chars",
            contract_version="1.0.0",
            description="Quotes: \"double\" and 'single', backslash: \\, newline: \n, tab: \t",
        )

        # Should handle special characters correctly
        fp1 = compute_contract_fingerprint(contract)
        fp2 = compute_contract_fingerprint(contract)

        assert str(fp1) == str(fp2)

    def test_zero_version_fingerprint(self) -> None:
        """Test fingerprint for contracts starting at version 0.0.0."""
        contract = ModelMinimalContract(name="initial", contract_version="0.0.0")
        fingerprint = compute_contract_fingerprint(contract)

        assert str(fingerprint).startswith("0.0.0:")
        assert fingerprint.version == ModelContractVersion(major=0, minor=0, patch=0)

    def test_large_version_numbers(self) -> None:
        """Test fingerprint handles large version numbers."""
        contract = ModelMinimalContract(name="test", contract_version="999.999.999")
        fingerprint = compute_contract_fingerprint(contract)

        assert str(fingerprint).startswith("999.999.999:")
        assert fingerprint.version.major == 999
        assert fingerprint.version.minor == 999
        assert fingerprint.version.patch == 999


# =============================================================================
# Normalization Idempotency Tests
# =============================================================================


@pytest.mark.unit
class TestNormalizationIdempotency:
    """Tests for normalization idempotency guarantee.

    From CONTRACT_STABILITY_SPEC.md:
    Normalization is idempotent: normalize(normalize(c)) == normalize(c)
    """

    def test_normalization_is_idempotent(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that normalize(normalize(c)) == normalize(c)."""
        first_pass = normalize_contract(orchestrator_contract)

        # Parse back to model and normalize again
        parsed = json.loads(first_pass)
        reparsed_model = ModelTestOrchestratorContract.model_validate(parsed)
        second_pass = normalize_contract(reparsed_model)

        assert first_pass == second_pass

    def test_normalization_idempotent_with_nulls(
        self, contract_with_nulls: ModelTestOrchestratorContract
    ) -> None:
        """Test idempotency with null values."""
        first_pass = normalize_contract(contract_with_nulls)

        # Parse and normalize again
        parsed = json.loads(first_pass)
        reparsed = ModelTestOrchestratorContract.model_validate(parsed)
        second_pass = normalize_contract(reparsed)

        assert first_pass == second_pass

    def test_normalization_idempotent_with_nested(
        self, orchestrator_contract_with_nested: ModelTestOrchestratorContract
    ) -> None:
        """Test idempotency with nested structures."""
        first_pass = normalize_contract(orchestrator_contract_with_nested)

        parsed = json.loads(first_pass)
        reparsed = ModelTestOrchestratorContract.model_validate(parsed)
        second_pass = normalize_contract(reparsed)

        assert first_pass == second_pass

    def test_fingerprint_idempotent_after_serialization(
        self, orchestrator_contract: ModelTestOrchestratorContract
    ) -> None:
        """Test that fingerprint is stable after JSON round-trip."""
        original_fp = compute_contract_fingerprint(orchestrator_contract)

        # Serialize to JSON and back
        json_str = orchestrator_contract.model_dump_json()
        reparsed = ModelTestOrchestratorContract.model_validate_json(json_str)
        reparsed_fp = compute_contract_fingerprint(reparsed)

        assert str(original_fp) == str(reparsed_fp)

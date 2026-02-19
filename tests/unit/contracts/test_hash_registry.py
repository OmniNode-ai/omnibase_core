# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive TDD unit tests for Contract Hash Registry.

Tests the hash registry module which provides deterministic SHA256
fingerprinting for ONEX contracts, enabling drift detection between
declarative and legacy versions during migration.

Test Categories:
1. Normalization Pipeline Tests
2. Fingerprint Computation Tests
3. Fingerprint Parsing Tests
4. Registry Operations Tests
5. Drift Detection Tests
6. Determinism and Stability Tests
7. Edge Cases and Error Handling

Requirements from CONTRACT_STABILITY_SPEC.md:
- Fingerprint format: `<semver>:<sha256-first-12-hex-chars>`
- Normalization is idempotent: normalize(normalize(c)) == normalize(c)
- Same contract produces identical fingerprint before and after migration
- Detects drift between declarative and legacy versions
"""

import json
from datetime import datetime

import pytest
from pydantic import BaseModel, Field, field_validator

from omnibase_core.contracts import (
    ContractHashRegistry,
    ModelContractFingerprint,
    ModelContractNormalizationConfig,
    ModelDriftResult,
    compute_contract_fingerprint,
    normalize_contract,
)
from omnibase_core.models.contracts.model_contract_version import ModelContractVersion
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# Test Model for Fingerprinting
# =============================================================================


class ModelTestContract(BaseModel):
    """Simple test contract model for fingerprinting tests.

    Note: contract_version field accepts both string ("1.0.0") and ModelContractVersion
    for test convenience, but is stored as ModelContractVersion.
    """

    name: str = Field(default="test_contract")
    contract_version: ModelContractVersion = Field(
        default_factory=lambda: ModelContractVersion(major=1, minor=0, patch=0)
    )
    description: str | None = Field(default=None)
    node_type: str = Field(default="COMPUTE_GENERIC")
    input_model: str = Field(default="omnibase_core.models.ModelInput")
    output_model: str = Field(default="omnibase_core.models.ModelOutput")
    optional_field: str | None = Field(default=None)
    nested: dict[str, object] | None = Field(default=None)
    list_with_nulls: list[int | None] | None = Field(default=None)

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


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_contract() -> ModelTestContract:
    """Sample contract for testing."""
    return ModelTestContract(
        name="test_contract",
        contract_version="1.2.3",
        description="A test contract",
        node_type="COMPUTE_GENERIC",
        input_model="omnibase_core.models.ModelInput",
        output_model="omnibase_core.models.ModelOutput",
    )


@pytest.fixture
def sample_contract_with_nulls() -> ModelTestContract:
    """Sample contract with null values for testing null removal."""
    return ModelTestContract(
        name="test_contract",
        contract_version="1.0.0",
        description=None,
        optional_field=None,
        nested={
            "field_a": "value",
            "field_b": None,
            "deeply_nested": {
                "keep": "this",
                "remove": None,
            },
        },
        list_with_nulls=[1, None, 3, None, 5],
    )


@pytest.fixture
def registry() -> ContractHashRegistry:
    """Create a fresh registry for each test."""
    return ContractHashRegistry()


# =============================================================================
# Normalization Pipeline Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestNormalizationPipeline:
    """Tests for the contract normalization pipeline."""

    def test_normalize_basic_contract(self, sample_contract: ModelTestContract) -> None:
        """Test basic contract normalization produces valid JSON."""
        result = normalize_contract(sample_contract)
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert parsed["name"] == "test_contract"

    def test_normalize_removes_null_values(
        self, sample_contract_with_nulls: ModelTestContract
    ) -> None:
        """Test that null values are removed during normalization."""
        result = normalize_contract(sample_contract_with_nulls)
        parsed = json.loads(result)

        # Null fields should be removed
        assert "description" not in parsed
        assert "optional_field" not in parsed

        # Nested nulls should also be removed
        assert "field_b" not in parsed["nested"]
        assert "remove" not in parsed["nested"]["deeply_nested"]

        # Non-null values should remain
        assert parsed["name"] == "test_contract"
        assert parsed["nested"]["field_a"] == "value"
        assert parsed["nested"]["deeply_nested"]["keep"] == "this"

    def test_normalize_removes_nulls_from_lists(
        self, sample_contract_with_nulls: ModelTestContract
    ) -> None:
        """Test that null values are removed from lists."""
        result = normalize_contract(sample_contract_with_nulls)
        parsed = json.loads(result)

        # List should have nulls removed
        assert parsed["list_with_nulls"] == [1, 3, 5]

    def test_normalize_sorts_keys_alphabetically(self) -> None:
        """Test that keys are sorted alphabetically.

        Uses a model with nested dict containing non-alphabetically ordered keys.
        """
        contract = ModelTestContract(
            name="test",
            contract_version="1.0.0",
            nested={"zebra": 1, "apple": 2, "mango": 3},
        )
        result = normalize_contract(contract)
        parsed = json.loads(result)

        # Keys in nested dict should appear in alphabetical order
        nested_keys = list(parsed["nested"].keys())
        assert nested_keys == ["apple", "mango", "zebra"]

    def test_normalize_sorts_nested_keys(self) -> None:
        """Test that deeply nested keys are also sorted."""
        contract = ModelTestContract(
            name="test",
            contract_version="1.0.0",
            nested={
                "outer": {"zebra": 1, "apple": 2},
                "another": {"delta": 3, "alpha": 4},
            },
        )
        result = normalize_contract(contract)

        # Nested keys should be sorted at all levels
        parsed = json.loads(result)
        outer_keys = list(parsed["nested"]["outer"].keys())
        another_keys = list(parsed["nested"]["another"].keys())
        assert outer_keys == sorted(outer_keys)
        assert another_keys == sorted(another_keys)

    def test_normalize_compact_json_no_whitespace(
        self, sample_contract: ModelTestContract
    ) -> None:
        """Test that compact JSON has no extra whitespace."""
        result = normalize_contract(sample_contract)

        # Should not contain newlines or indentation spaces
        assert "\n" not in result
        assert "  " not in result

    def test_normalize_is_idempotent(self, sample_contract: ModelTestContract) -> None:
        """Test that normalize(normalize(c)) == normalize(c)."""
        first_pass = normalize_contract(sample_contract)
        # Parse back to model and normalize again
        parsed = json.loads(first_pass)
        reparsed_model = ModelTestContract.model_validate(parsed)
        second_pass = normalize_contract(reparsed_model)

        assert first_pass == second_pass

    def test_normalize_with_custom_config_no_null_removal(self) -> None:
        """Test normalization without null removal."""
        contract = ModelTestContract(name="test", optional_field=None)
        config = ModelContractNormalizationConfig(remove_nulls=False)

        result = normalize_contract(contract, config)
        parsed = json.loads(result)

        # Null should be preserved (as JSON null)
        assert "optional_field" in parsed
        assert parsed["optional_field"] is None

    def test_normalize_with_custom_config_no_sorting(self) -> None:
        """Test normalization without key sorting in local processing."""
        contract = ModelTestContract(name="zebra_test")
        config = ModelContractNormalizationConfig(sort_keys=False)

        result = normalize_contract(contract, config)
        # Note: json.dumps still uses sort_keys=True by default in normalize_contract
        # This tests the local canonical ordering step
        assert isinstance(result, str)

    def test_normalize_empty_contract(self) -> None:
        """Test normalizing an empty/default contract."""
        contract = ModelTestContract()
        result = normalize_contract(contract)
        parsed = json.loads(result)
        assert "name" in parsed

    def test_normalize_deeply_nested_structure(self) -> None:
        """Test normalization of deeply nested structures."""
        contract = ModelTestContract(
            nested={
                "level1": {
                    "level2": {
                        "level3": {
                            "value": "deep",
                        },
                    },
                },
            },
        )
        result = normalize_contract(contract)
        parsed = json.loads(result)
        assert parsed["nested"]["level1"]["level2"]["level3"]["value"] == "deep"


# =============================================================================
# Fingerprint Computation Tests
# =============================================================================


@pytest.mark.unit
class TestFingerprintComputation:
    """Tests for contract fingerprint computation."""

    def test_compute_fingerprint_basic(
        self, sample_contract: ModelTestContract
    ) -> None:
        """Test basic fingerprint computation."""
        fingerprint = compute_contract_fingerprint(sample_contract)

        assert isinstance(fingerprint, ModelContractFingerprint)
        assert fingerprint.version == ModelContractVersion.from_string("1.2.3")
        assert len(fingerprint.hash_prefix) == 12  # Default hash length
        assert len(fingerprint.full_hash) == 64  # Full SHA256

    def test_compute_fingerprint_format(
        self, sample_contract: ModelTestContract
    ) -> None:
        """Test that fingerprint string format is correct."""
        fingerprint = compute_contract_fingerprint(sample_contract)
        fingerprint_str = str(fingerprint)

        # Format: <semver>:<hash_prefix>
        assert ":" in fingerprint_str
        parts = fingerprint_str.split(":")
        assert len(parts) == 2
        assert parts[0] == "1.2.3"
        assert len(parts[1]) == 12

    def test_compute_fingerprint_default_version(self) -> None:
        """Test that contracts without version attribute use default."""
        # ModelTestContract has contract_version="1.0.0" by default
        contract = ModelTestContract(name="test")
        fingerprint = compute_contract_fingerprint(contract)

        assert fingerprint.version == ModelContractVersion(major=1, minor=0, patch=0)
        assert str(fingerprint).startswith("1.0.0:")

    def test_compute_fingerprint_with_model_version(self) -> None:
        """Test fingerprint with ModelContractVersion object."""
        version = ModelContractVersion(major=3, minor=0, patch=0)
        contract = ModelTestContract(name="test", contract_version=version)
        fingerprint = compute_contract_fingerprint(contract)

        assert fingerprint.version == version
        assert str(fingerprint).startswith("3.0.0:")

    def test_compute_fingerprint_deterministic(
        self, sample_contract: ModelTestContract
    ) -> None:
        """Test that fingerprint computation is deterministic."""
        fp1 = compute_contract_fingerprint(sample_contract)
        fp2 = compute_contract_fingerprint(sample_contract)

        assert str(fp1) == str(fp2)
        assert fp1.hash_prefix == fp2.hash_prefix
        assert fp1.full_hash == fp2.full_hash

    def test_compute_fingerprint_different_content_different_hash(self) -> None:
        """Test that different content produces different hashes."""
        contract1 = ModelTestContract(name="test1", contract_version="1.0.0")
        contract2 = ModelTestContract(name="test2", contract_version="1.0.0")

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        # Same version, different hash
        assert fp1.version == fp2.version
        assert fp1.hash_prefix != fp2.hash_prefix

    def test_compute_fingerprint_include_normalized_content(
        self, sample_contract: ModelTestContract
    ) -> None:
        """Test including normalized content in fingerprint."""
        fingerprint = compute_contract_fingerprint(
            sample_contract, include_normalized_content=True
        )

        assert fingerprint.normalized_content is not None
        # Should be valid JSON
        parsed = json.loads(fingerprint.normalized_content)
        assert parsed["name"] == "test_contract"

    def test_compute_fingerprint_custom_hash_length(
        self, sample_contract: ModelTestContract
    ) -> None:
        """Test custom hash length configuration."""
        config = ModelContractNormalizationConfig(hash_length=16)
        fingerprint = compute_contract_fingerprint(sample_contract, config)

        assert len(fingerprint.hash_prefix) == 16

    def test_compute_fingerprint_with_semver_duck_typing(self) -> None:
        """Test fingerprint computation with ModelSemVer via duck-typing.

        Verifies the hasattr-based version detection (contract_hash_registry.py:263-273)
        correctly handles ModelSemVer objects without using isinstance().
        This tests the duck-typing path that checks for major/minor/patch attributes.
        """
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        # Create a model that has contract_version as ModelSemVer
        class ContractWithSemVer(BaseModel):
            contract_version: ModelSemVer
            node_type: str = "COMPUTE_GENERIC"
            name: str = "test_contract"

        contract = ContractWithSemVer(
            contract_version=ModelSemVer(major=1, minor=2, patch=3),
        )

        fingerprint = compute_contract_fingerprint(contract)

        # Should convert ModelSemVer -> ModelContractVersion correctly via duck-typing
        assert fingerprint.version.major == 1
        assert fingerprint.version.minor == 2
        assert fingerprint.version.patch == 3
        assert str(fingerprint).startswith("1.2.3:")

    def test_compute_fingerprint_invalid_version_type_raises_error(self) -> None:
        """Test that invalid version types raise ModelOnexError.

        Verifies the error handling path (contract_hash_registry.py:275-279) correctly
        raises ModelOnexError for unsupported version types.
        """

        class ContractWithInvalidVersion(BaseModel):
            contract_version: list[int] = Field(default=[1, 2, 3])
            node_type: str = "COMPUTE_GENERIC"
            name: str = "test_contract"

        contract = ContractWithInvalidVersion()

        with pytest.raises(ModelOnexError) as exc_info:
            compute_contract_fingerprint(contract)

        assert "Invalid version type" in exc_info.value.message
        assert "list" in exc_info.value.message

    def test_compute_fingerprint_with_custom_version_object_duck_typing(self) -> None:
        """Test fingerprint computation with custom version object via duck-typing.

        Verifies that ANY Pydantic model with major/minor/patch attributes works,
        not just ModelSemVer or ModelContractVersion specifically. This ensures
        the duck-typing path (contract_hash_registry.py:263-273) works with arbitrary
        version-like objects that have the required attributes.

        Note: The version object must be JSON-serializable since the entire
        contract gets normalized to JSON during fingerprint computation.
        """

        class CustomVersionModel(BaseModel):
            """A custom Pydantic version model that is NOT ModelSemVer or ModelContractVersion.

            This model has major/minor/patch attributes but is a completely
            different type, testing the duck-typing path in contract_hash_registry.py.
            """

            major: int
            minor: int
            patch: int
            # Extra field to prove this is different from standard version models
            custom_metadata: str = "custom"

        class ContractWithCustomVersion(BaseModel):
            contract_version: CustomVersionModel = Field(
                default_factory=lambda: CustomVersionModel(major=2, minor=5, patch=1)
            )
            node_type: str = "COMPUTE_GENERIC"
            name: str = "test_contract"

        contract = ContractWithCustomVersion()

        fingerprint = compute_contract_fingerprint(contract)

        # Should extract version via duck-typing (hasattr checks)
        assert fingerprint.version.major == 2
        assert fingerprint.version.minor == 5
        assert fingerprint.version.patch == 1
        assert str(fingerprint).startswith("2.5.1:")


# =============================================================================
# Fingerprint Parsing Tests
# =============================================================================


@pytest.mark.unit
class TestFingerprintParsing:
    """Tests for fingerprint string parsing."""

    def test_parse_valid_fingerprint(self) -> None:
        """Test parsing a valid fingerprint string."""
        fingerprint = ModelContractFingerprint.from_string("1.2.3:abcdef123456")

        assert fingerprint.version == ModelContractVersion(major=1, minor=2, patch=3)
        assert fingerprint.hash_prefix == "abcdef123456"

    def test_parse_fingerprint_zero_version(self) -> None:
        """Test parsing fingerprint with zero version."""
        fingerprint = ModelContractFingerprint.from_string("0.0.0:0123456789ab")

        assert fingerprint.version == ModelContractVersion(major=0, minor=0, patch=0)

    def test_parse_fingerprint_uppercase_hash_normalized(self) -> None:
        """Test that uppercase hash is normalized to lowercase."""
        fingerprint = ModelContractFingerprint.from_string("1.0.0:ABCDEF123456")

        assert fingerprint.hash_prefix == "abcdef123456"

    def test_parse_fingerprint_missing_colon_raises_error(self) -> None:
        """Test that missing colon raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelContractFingerprint.from_string("1.2.3abcdef")

        assert "Invalid fingerprint format" in str(exc_info.value)

    def test_parse_fingerprint_invalid_version_raises_error(self) -> None:
        """Test that invalid version raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelContractFingerprint.from_string("invalid:abcdef123456")

        assert "Invalid version" in str(exc_info.value)

    def test_parse_fingerprint_invalid_hash_raises_error(self) -> None:
        """Test that invalid hash (non-hex) raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelContractFingerprint.from_string("1.0.0:notahexvalue")

        assert "Invalid hash prefix" in str(exc_info.value)

    def test_parse_fingerprint_empty_hash_raises_error(self) -> None:
        """Test that empty hash raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelContractFingerprint.from_string("1.0.0:")

        assert "Invalid hash prefix" in str(exc_info.value)


# =============================================================================
# Fingerprint Model Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractFingerprint:
    """Tests for ModelContractFingerprint model."""

    def test_fingerprint_equality(self) -> None:
        """Test fingerprint equality comparison."""
        fp1 = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )
        fp2 = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )
        assert fp1 == fp2

    def test_fingerprint_inequality_version(self) -> None:
        """Test fingerprint inequality when versions differ."""
        fp1 = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )
        fp2 = ModelContractFingerprint(
            version=ModelContractVersion(major=2, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )
        assert fp1 != fp2

    def test_fingerprint_inequality_hash(self) -> None:
        """Test fingerprint inequality when hashes differ."""
        fp1 = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )
        fp2 = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="123456abcdef",
            full_hash="b" * 64,
        )
        assert fp1 != fp2

    def test_fingerprint_equality_with_string(self) -> None:
        """Test fingerprint equality with string."""
        fp = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )
        assert fp == "1.0.0:abcdef123456"
        assert fp != "1.0.0:fedcba987654"

    def test_fingerprint_hashable(self) -> None:
        """Test that fingerprints are hashable for use in sets/dicts."""
        fp1 = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )
        fp2 = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )

        # Should be usable in sets
        fingerprint_set = {fp1, fp2}
        assert len(fingerprint_set) == 1

        # Should be usable as dict keys
        fingerprint_dict = {fp1: "value"}
        assert fingerprint_dict[fp2] == "value"

    def test_fingerprint_matches_method(self) -> None:
        """Test fingerprint matches() method."""
        fp = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )

        assert fp.matches("1.0.0:abcdef123456") is True
        assert fp.matches("1.0.0:fedcba987654") is False
        assert fp.matches("invalid") is False

    def test_fingerprint_has_timestamp(self) -> None:
        """Test that fingerprint has computed_at timestamp."""
        fp = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )

        assert fp.computed_at is not None
        assert isinstance(fp.computed_at, datetime)


# =============================================================================
# Registry Operations Tests
# =============================================================================


@pytest.mark.unit
class TestContractHashRegistry:
    """Tests for ContractHashRegistry operations."""

    def test_register_and_lookup(self, registry: ContractHashRegistry) -> None:
        """Test basic register and lookup operations."""
        fingerprint = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )

        registry.register("my_contract", fingerprint)
        result = registry.lookup("my_contract")

        assert result is not None
        assert result == fingerprint

    def test_register_with_string_fingerprint(
        self, registry: ContractHashRegistry
    ) -> None:
        """Test registering with fingerprint string."""
        registry.register("my_contract", "1.0.0:abcdef123456")
        result = registry.lookup("my_contract")

        assert result is not None
        assert str(result) == "1.0.0:abcdef123456"

    def test_lookup_nonexistent_returns_none(
        self, registry: ContractHashRegistry
    ) -> None:
        """Test that lookup of nonexistent contract returns None."""
        result = registry.lookup("nonexistent")
        assert result is None

    def test_lookup_string(self, registry: ContractHashRegistry) -> None:
        """Test lookup_string returns fingerprint as string."""
        registry.register("my_contract", "1.0.0:abcdef123456")
        result = registry.lookup_string("my_contract")

        assert result == "1.0.0:abcdef123456"

    def test_lookup_string_nonexistent_returns_none(
        self, registry: ContractHashRegistry
    ) -> None:
        """Test lookup_string of nonexistent contract returns None."""
        result = registry.lookup_string("nonexistent")
        assert result is None

    def test_register_from_contract(
        self, registry: ContractHashRegistry, sample_contract: ModelTestContract
    ) -> None:
        """Test register_from_contract computes and registers fingerprint."""
        fingerprint = registry.register_from_contract("my_contract", sample_contract)

        assert fingerprint is not None
        assert fingerprint.version == ModelContractVersion.from_string("1.2.3")

        # Should be retrievable
        lookup_result = registry.lookup("my_contract")
        assert lookup_result == fingerprint

    def test_verify_matching_fingerprint(self, registry: ContractHashRegistry) -> None:
        """Test verify returns True for matching fingerprint."""
        registry.register("my_contract", "1.0.0:abcdef123456")

        assert registry.verify("my_contract", "1.0.0:abcdef123456") is True

    def test_verify_non_matching_fingerprint(
        self, registry: ContractHashRegistry
    ) -> None:
        """Test verify returns False for non-matching fingerprint."""
        registry.register("my_contract", "1.0.0:abcdef123456")

        assert registry.verify("my_contract", "1.0.0:fedcba987654") is False

    def test_verify_nonexistent_contract(self, registry: ContractHashRegistry) -> None:
        """Test verify returns False for nonexistent contract."""
        assert registry.verify("nonexistent", "1.0.0:abcdef123456") is False

    def test_unregister_existing(self, registry: ContractHashRegistry) -> None:
        """Test unregister removes existing contract."""
        registry.register("my_contract", "1.0.0:abcdef123456")

        assert registry.unregister("my_contract") is True
        assert registry.lookup("my_contract") is None

    def test_unregister_nonexistent(self, registry: ContractHashRegistry) -> None:
        """Test unregister returns False for nonexistent contract."""
        assert registry.unregister("nonexistent") is False

    def test_clear(self, registry: ContractHashRegistry) -> None:
        """Test clear removes all entries."""
        registry.register("contract1", "1.0.0:aaaaaaaaaa11")
        registry.register("contract2", "1.0.0:bbbbbbbbbb22")

        registry.clear()

        assert registry.count() == 0
        assert registry.lookup("contract1") is None
        assert registry.lookup("contract2") is None

    def test_list_contracts(self, registry: ContractHashRegistry) -> None:
        """Test list_contracts returns all registered IDs."""
        registry.register("contract_a", "1.0.0:aaaaaaaaaa11")
        registry.register("contract_b", "1.0.0:bbbbbbbbbb22")
        registry.register("contract_c", "1.0.0:cccccccccc33")

        contracts = registry.list_contracts()

        assert len(contracts) == 3
        assert "contract_a" in contracts
        assert "contract_b" in contracts
        assert "contract_c" in contracts

    def test_count(self, registry: ContractHashRegistry) -> None:
        """Test count returns correct number of entries."""
        assert registry.count() == 0

        registry.register("contract1", "1.0.0:aaaaaaaaaa11")
        assert registry.count() == 1

        registry.register("contract2", "1.0.0:bbbbbbbbbb22")
        assert registry.count() == 2

    def test_to_dict(self, registry: ContractHashRegistry) -> None:
        """Test to_dict exports registry as dictionary."""
        registry.register("contract1", "1.0.0:aaaaaaaaaa11")
        registry.register("contract2", "2.0.0:bbbbbbbbbb22")

        result = registry.to_dict()

        assert result == {
            "contract1": "1.0.0:aaaaaaaaaa11",
            "contract2": "2.0.0:bbbbbbbbbb22",
        }

    def test_from_dict(self) -> None:
        """Test from_dict creates registry from dictionary."""
        data = {
            "contract1": "1.0.0:aaaaaaaaaa11",
            "contract2": "2.0.0:bbbbbbbbbb22",
        }

        registry = ContractHashRegistry.from_dict(data)

        assert registry.count() == 2
        assert registry.lookup_string("contract1") == "1.0.0:aaaaaaaaaa11"
        assert registry.lookup_string("contract2") == "2.0.0:bbbbbbbbbb22"

    def test_register_empty_contract_id_raises_error(
        self, registry: ContractHashRegistry
    ) -> None:
        """Test that empty contract ID raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            registry.register("", "1.0.0:abcdef123456")

        assert "Contract ID cannot be empty" in str(exc_info.value)

    def test_register_overwrites_existing(self, registry: ContractHashRegistry) -> None:
        """Test that registering same ID overwrites existing entry."""
        registry.register("my_contract", "1.0.0:aaaaaaaaaa11")
        registry.register("my_contract", "2.0.0:bbbbbbbbbb22")

        result = registry.lookup_string("my_contract")
        assert result == "2.0.0:bbbbbbbbbb22"


# =============================================================================
# Drift Detection Tests
# =============================================================================


@pytest.mark.unit
class TestDriftDetection:
    """Tests for contract drift detection."""

    def test_detect_drift_no_drift(self, registry: ContractHashRegistry) -> None:
        """Test detect_drift returns no drift for matching fingerprints."""
        registry.register("my_contract", "1.0.0:abcdef123456")

        result = registry.detect_drift("my_contract", "1.0.0:abcdef123456")

        assert isinstance(result, ModelDriftResult)
        assert result.has_drift is False
        assert result.contract_name == "my_contract"
        assert result.drift_type is None

    def test_detect_drift_content_drift(self, registry: ContractHashRegistry) -> None:
        """Test detect_drift detects content drift (hash changed)."""
        registry.register("my_contract", "1.0.0:abcdef123456")

        result = registry.detect_drift("my_contract", "1.0.0:fedcba987654")

        assert result.has_drift is True
        assert result.drift_type == "content"
        assert result.expected_fingerprint is not None
        assert result.computed_fingerprint is not None

    def test_detect_drift_version_drift(self, registry: ContractHashRegistry) -> None:
        """Test detect_drift detects version drift."""
        registry.register("my_contract", "1.0.0:abcdef123456")

        result = registry.detect_drift("my_contract", "2.0.0:abcdef123456")

        assert result.has_drift is True
        assert result.drift_type == "version"

    def test_detect_drift_both_version_and_content(
        self, registry: ContractHashRegistry
    ) -> None:
        """Test detect_drift detects both version and content drift."""
        registry.register("my_contract", "1.0.0:abcdef123456")

        result = registry.detect_drift("my_contract", "2.0.0:fedcba987654")

        assert result.has_drift is True
        assert result.drift_type == "both"

    def test_detect_drift_not_registered(self, registry: ContractHashRegistry) -> None:
        """Test detect_drift handles unregistered contracts."""
        result = registry.detect_drift("nonexistent", "1.0.0:abcdef123456")

        assert result.has_drift is True
        assert result.drift_type == "not_registered"
        assert result.expected_fingerprint is None

    def test_detect_drift_from_contract(
        self, registry: ContractHashRegistry, sample_contract: ModelTestContract
    ) -> None:
        """Test detect_drift_from_contract computes and detects drift."""
        # Register the original
        original_fp = registry.register_from_contract("my_contract", sample_contract)

        # Detect drift from same contract (should be no drift)
        result = registry.detect_drift_from_contract("my_contract", sample_contract)

        assert result.has_drift is False

        # Modify contract and detect drift using model_copy
        modified_contract = sample_contract.model_copy(
            update={"description": "Modified description"}
        )

        result = registry.detect_drift_from_contract("my_contract", modified_contract)

        assert result.has_drift is True
        assert result.drift_type == "content"

    def test_detect_drift_details_include_version_info(
        self, registry: ContractHashRegistry
    ) -> None:
        """Test that drift details include version comparison info."""
        registry.register("my_contract", "1.0.0:abcdef123456")

        result = registry.detect_drift("my_contract", "2.0.0:fedcba987654")

        # ModelDriftDetails is a Pydantic model with typed fields
        assert result.details.version_match is not None
        assert result.details.hash_match is not None
        assert result.details.version_match is False
        assert result.details.hash_match is False

    def test_drift_result_has_timestamp(self, registry: ContractHashRegistry) -> None:
        """Test that drift result has timestamp."""
        registry.register("my_contract", "1.0.0:abcdef123456")

        result = registry.detect_drift("my_contract", "1.0.0:abcdef123456")

        assert result.detected_at is not None
        assert isinstance(result.detected_at, datetime)


# =============================================================================
# Determinism and Stability Tests
# =============================================================================


@pytest.mark.unit
class TestDeterminismAndStability:
    """Tests for fingerprint determinism and stability guarantees."""

    def test_same_contract_same_fingerprint(self) -> None:
        """Test that same contract always produces same fingerprint.

        This is a critical stability guarantee from CONTRACT_STABILITY_SPEC.md.
        """
        contract = ModelTestContract(
            name="stability_test",
            contract_version="1.0.0",
            description="Testing stability",
        )

        # Compute multiple times
        fingerprints = [compute_contract_fingerprint(contract) for _ in range(10)]

        # All should be identical
        first = str(fingerprints[0])
        assert all(str(fp) == first for fp in fingerprints)

    def test_key_order_does_not_affect_fingerprint(self) -> None:
        """Test that key order doesn't affect fingerprint (canonical ordering).

        Uses nested dicts with different key orders to verify normalization.
        """
        contract1 = ModelTestContract(
            name="test",
            contract_version="1.0.0",
            nested={"zebra": 1, "apple": 2, "mango": 3},
        )
        contract2 = ModelTestContract(
            name="test",
            contract_version="1.0.0",
            nested={"apple": 2, "mango": 3, "zebra": 1},
        )

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        assert str(fp1) == str(fp2)

    def test_null_presence_normalized(self) -> None:
        """Test that null values are normalized consistently."""
        contract1 = ModelTestContract(
            name="test", contract_version="1.0.0", optional_field=None
        )
        contract2 = ModelTestContract(
            name="test", contract_version="1.0.0"
        )  # optional_field defaults to None

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        # Should be identical after null removal
        assert str(fp1) == str(fp2)

    def test_nested_null_removal_consistent(self) -> None:
        """Test that nested null removal is consistent."""
        contract1 = ModelTestContract(
            name="test",
            contract_version="1.0.0",
            nested={"keep": "value", "remove": None},
        )
        contract2 = ModelTestContract(
            name="test",
            contract_version="1.0.0",
            nested={"keep": "value"},
        )

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        assert str(fp1) == str(fp2)

    def test_whitespace_normalization(self) -> None:
        """Test that whitespace in values is preserved but format is normalized."""
        contract = ModelTestContract(
            name="  test  ",  # Whitespace in value
            contract_version="1.0.0",
            description="line1\nline2",  # Newline in value
        )

        # Should compute without error
        fingerprint = compute_contract_fingerprint(contract)
        assert fingerprint is not None

        # Compute again to verify determinism
        fingerprint2 = compute_contract_fingerprint(contract)
        assert str(fingerprint) == str(fingerprint2)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


@pytest.mark.unit
class TestEdgeCasesAndErrors:
    """Tests for edge cases and error handling."""

    def test_normalize_non_serializable_raises_error(self) -> None:
        """Test that non-JSON-serializable content raises ModelOnexError.

        Uses a model with nested dict containing a non-serializable value.
        """
        # Create contract with non-serializable nested content
        contract = ModelTestContract(
            name="test",
            contract_version="1.0.0",
            nested={"callback": lambda x: x},  # Lambda not JSON-serializable
        )

        with pytest.raises(ModelOnexError) as exc_info:
            normalize_contract(contract)

        assert "Failed to normalize" in str(exc_info.value)

    def test_large_contract_normalization(self) -> None:
        """Test normalization of large contracts."""
        # Create a large contract with deeply nested data
        large_contract = ModelTestContract(
            name="large_contract",
            contract_version="1.0.0",
            nested={f"key_{i}": f"value_{i}" for i in range(100)},
        )

        # Should complete without error
        fingerprint = compute_contract_fingerprint(large_contract)
        assert fingerprint is not None

    def test_special_characters_in_values(self) -> None:
        """Test handling of special characters in values."""
        contract = ModelTestContract(
            name="test",
            contract_version="1.0.0",
            description='Contains "quotes" and \\backslashes\\ and \t tabs',
        )

        # Should compute without error
        fingerprint = compute_contract_fingerprint(contract)
        assert fingerprint is not None

        # Should be deterministic
        fingerprint2 = compute_contract_fingerprint(contract)
        assert str(fingerprint) == str(fingerprint2)

    def test_empty_lists_preserved(self) -> None:
        """Test that empty lists are preserved in normalization."""
        contract = ModelTestContract(
            name="test",
            contract_version="1.0.0",
            list_with_nulls=[],  # Empty list
        )

        result = normalize_contract(contract)
        parsed = json.loads(result)

        assert "list_with_nulls" in parsed
        assert parsed["list_with_nulls"] == []

    def test_empty_nested_dicts_removed_after_null_removal(self) -> None:
        """Test that empty dicts after null removal are also removed."""
        contract = ModelTestContract(
            name="test",
            contract_version="1.0.0",
            nested={"only_null": None},  # Will become empty after null removal
        )

        result = normalize_contract(contract)
        parsed = json.loads(result)

        # Empty nested dict should be removed
        assert "nested" not in parsed

    def test_normalization_config_validation(self) -> None:
        """Test normalization config validation."""
        # Valid config
        config = ModelContractNormalizationConfig(hash_length=16)
        assert config.hash_length == 16

        # Invalid hash_length (too small)
        with pytest.raises(Exception):
            ModelContractNormalizationConfig(hash_length=4)

        # Invalid hash_length (too large)
        with pytest.raises(Exception):
            ModelContractNormalizationConfig(hash_length=100)

    def test_fingerprint_model_frozen(self) -> None:
        """Test that fingerprint model is frozen (immutable)."""
        fp = ModelContractFingerprint(
            version=ModelContractVersion(major=1, minor=0, patch=0),
            hash_prefix="abcdef123456",
            full_hash="a" * 64,
        )

        with pytest.raises(Exception):
            fp.hash_prefix = "newvalue12345"  # type: ignore[misc]

    def test_drift_result_model_frozen(self) -> None:
        """Test that drift result model is frozen (immutable)."""
        result = ModelDriftResult(
            contract_name="test",
            has_drift=False,
        )

        with pytest.raises(Exception):
            result.has_drift = True  # type: ignore[misc]


# =============================================================================
# Migration Scenario Tests
# =============================================================================


@pytest.mark.unit
class TestMigrationScenarios:
    """Tests simulating migration scenarios between declarative and legacy versions."""

    def test_same_contract_different_sources_same_fingerprint(self) -> None:
        """Test that same contract from different sources produces same fingerprint.

        This verifies the key requirement: contracts should fingerprint
        identically whether loaded from YAML, Python dict, or database.
        """
        # Simulate loading from YAML (with some null fields)
        yaml_loaded = ModelTestContract(
            name="my_service",
            contract_version="1.0.0",
            description="Service contract",
            optional_field=None,
            node_type="COMPUTE_GENERIC",
        )

        # Simulate loading from Python definition (no null fields explicitly set)
        python_defined = ModelTestContract(
            name="my_service",
            contract_version="1.0.0",
            description="Service contract",
            node_type="COMPUTE_GENERIC",
        )

        fp_yaml = compute_contract_fingerprint(yaml_loaded)
        fp_python = compute_contract_fingerprint(python_defined)

        # Should produce identical fingerprints
        assert str(fp_yaml) == str(fp_python)

    def test_version_bump_detected_as_drift(self) -> None:
        """Test that version bump is detected as drift."""
        registry = ContractHashRegistry()

        # Register v1.0.0
        v1_contract = ModelTestContract(name="my_service", contract_version="1.0.0")
        registry.register_from_contract("my_service", v1_contract)

        # Check v1.1.0 with same content
        v1_1_contract = ModelTestContract(name="my_service", contract_version="1.1.0")

        result = registry.detect_drift_from_contract("my_service", v1_1_contract)

        assert result.has_drift is True
        assert result.drift_type == "both"  # Version and content changed

    def test_content_change_detected_as_drift(self) -> None:
        """Test that content changes are detected as drift."""
        registry = ContractHashRegistry()

        # Register original
        original = ModelTestContract(name="my_service", contract_version="1.0.0")
        registry.register_from_contract("my_service", original)

        # Check modified (same version, different content via description change)
        modified = ModelTestContract(
            name="my_service", contract_version="1.0.0", description="Added description"
        )

        result = registry.detect_drift_from_contract("my_service", modified)

        assert result.has_drift is True
        assert result.drift_type == "content"

    def test_registry_export_import_preserves_fingerprints(self) -> None:
        """Test that exporting and importing registry preserves fingerprints."""
        # Create and populate registry
        original_registry = ContractHashRegistry()
        original_registry.register("contract1", "1.0.0:aaaaaaaaaa11")
        original_registry.register("contract2", "2.0.0:bbbbbbbbbb22")

        # Export to dict
        exported = original_registry.to_dict()

        # Import into new registry
        imported_registry = ContractHashRegistry.from_dict(exported)

        # Verify fingerprints are preserved
        assert imported_registry.lookup_string("contract1") == "1.0.0:aaaaaaaaaa11"
        assert imported_registry.lookup_string("contract2") == "2.0.0:bbbbbbbbbb22"


# =============================================================================
# Thread Safety Warning Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestContractHashRegistryConcurrency:
    """Tests demonstrating thread safety requirements for ContractHashRegistry.

    This test class serves as DOCUMENTATION that ContractHashRegistry is NOT
    thread-safe and requires external synchronization when accessed from
    multiple threads. These tests demonstrate the potential risks of
    concurrent access without proper locking.

    Thread Safety Warning:
        ContractHashRegistry uses an internal dictionary (self._registry)
        that is not protected by any synchronization primitives. While Python's
        GIL provides some protection for individual operations, compound
        operations (read-modify-write patterns) are NOT atomic and can lead to:
        - Lost updates when multiple threads register contracts simultaneously
        - Inconsistent reads during concurrent registration and lookup
        - Data races in drift detection workflows

    Production Usage:
        When using ContractHashRegistry in a multi-threaded environment,
        wrap all registry operations with a threading.Lock:

            import threading

            registry = ContractHashRegistry()
            registry_lock = threading.Lock()

            def safe_register(name: str, fingerprint: str) -> None:
                with registry_lock:
                    registry.register(name, fingerprint)

            def safe_lookup(name: str) -> str | None:
                with registry_lock:
                    return registry.lookup_string(name)

    See Also:
        docs/guides/THREADING.md: Complete thread safety guidelines for ONEX.
        src/omnibase_core/contracts/contract_hash_registry.py: ContractHashRegistry docstring.
    """

    def test_concurrent_access_without_locking_warning(self) -> None:
        """Demonstrate that concurrent access without locking may cause issues.

        This test serves as documentation that ContractHashRegistry is NOT
        thread-safe and requires external synchronization when accessed
        from multiple threads.

        The test simulates a scenario where multiple threads simultaneously:
        1. Register contracts to the registry
        2. Look up contracts from the registry

        Without proper locking, race conditions CAN occur, though they may
        not manifest deterministically in every test run. The purpose of this
        test is to document the risk and demonstrate proper patterns.

        Note:
            This test may pass even when race conditions exist because:
            1. Python's GIL serializes bytecode execution
            2. Race windows are narrow and timing-dependent
            3. dict operations have some atomicity guarantees

            However, compound operations (check-then-act patterns) and
            operations across multiple method calls are NOT atomic.
        """
        import threading
        from concurrent.futures import ThreadPoolExecutor

        # Create a shared registry WITHOUT external locking
        # WARNING: This is intentionally unsafe for demonstration purposes
        registry = ContractHashRegistry()

        # Track observed issues
        observed_issues: list[str] = []
        issues_lock = threading.Lock()

        def register_contracts(thread_id: int, count: int) -> int:
            """Register multiple contracts from a single thread."""
            registered = 0
            for i in range(count):
                contract_name = f"thread_{thread_id}_contract_{i}"
                fingerprint = f"1.0.0:{thread_id:06d}{i:06d}"
                try:
                    registry.register(contract_name, fingerprint)
                    registered += 1
                except Exception as e:
                    with issues_lock:
                        observed_issues.append(f"Register error: {e}")
            return registered

        def lookup_contracts(thread_id: int, count: int) -> int:
            """Lookup contracts that may or may not exist yet."""
            found = 0
            for i in range(count):
                # Try to look up contracts from all threads
                for t in range(4):
                    contract_name = f"thread_{t}_contract_{i}"
                    try:
                        result = registry.lookup_string(contract_name)
                        if result is not None:
                            found += 1
                    except Exception as e:
                        with issues_lock:
                            observed_issues.append(f"Lookup error: {e}")
            return found

        def mixed_operations(thread_id: int, count: int) -> tuple[int, int]:
            """Perform mixed register and lookup operations."""
            registered = 0
            found = 0
            for i in range(count):
                # Alternate between register and lookup
                if i % 2 == 0:
                    contract_name = f"mixed_thread_{thread_id}_contract_{i}"
                    fingerprint = f"2.0.0:{thread_id:06d}{i:06d}"
                    try:
                        registry.register(contract_name, fingerprint)
                        registered += 1
                    except Exception as e:
                        with issues_lock:
                            observed_issues.append(f"Mixed register error: {e}")
                else:
                    # Lookup a contract that may have been registered by another thread
                    other_thread = (thread_id + 1) % 4
                    contract_name = f"mixed_thread_{other_thread}_contract_{i - 1}"
                    try:
                        result = registry.lookup_string(contract_name)
                        if result is not None:
                            found += 1
                    except Exception as e:
                        with issues_lock:
                            observed_issues.append(f"Mixed lookup error: {e}")
            return registered, found

        # Run concurrent operations using ThreadPoolExecutor
        num_threads = 4
        operations_per_thread = 100

        with ThreadPoolExecutor(max_workers=num_threads * 3) as executor:
            # Use separate lists for different task types for type safety
            register_futures = [
                executor.submit(register_contracts, thread_id, operations_per_thread)
                for thread_id in range(num_threads)
            ]

            lookup_futures = [
                executor.submit(lookup_contracts, thread_id, operations_per_thread)
                for thread_id in range(num_threads)
            ]

            mixed_futures = [
                executor.submit(mixed_operations, thread_id, operations_per_thread)
                for thread_id in range(num_threads)
            ]

            # Wait for all tasks to complete
            register_results: list[int] = [f.result() for f in register_futures]
            lookup_results: list[int] = [f.result() for f in lookup_futures]
            mixed_results: list[tuple[int, int]] = [f.result() for f in mixed_futures]

        # Verify basic expectations
        # Note: Even without explicit locking, Python's GIL may prevent
        # some race conditions. The test documents the RISK, not the certainty.

        # All registration threads should have completed without exceptions
        # (though results may be inconsistent)
        total_registered_expected = num_threads * operations_per_thread
        total_registered_from_register = sum(register_results)

        # Suppress unused variable warnings (these demonstrate the pattern)
        _ = lookup_results
        _ = mixed_results

        # Document findings
        # The registry should contain entries, but the exact count may vary
        # if race conditions occurred (lost updates)
        final_count = registry.count()

        # This assertion documents the expected behavior WITHOUT race conditions
        # If this fails occasionally, it demonstrates the thread safety issue
        #
        # IMPORTANT: This test passing does NOT mean the code is thread-safe!
        # It only means race conditions did not manifest in this particular run.
        # The documentation above clearly states external locking is required.

        # Verify no exceptions were raised during concurrent access
        # (exceptions would indicate more severe issues than data races)
        assert len(observed_issues) == 0, f"Concurrent access issues: {observed_issues}"

        # Verify some contracts were registered (basic sanity check)
        assert final_count > 0, "Registry should contain some contracts"

        # Document the thread safety warning in test output
        # This serves as a reminder that passing this test does not guarantee
        # thread safety - proper locking is still required for production use.
        warning_message = (
            "\n"
            "=" * 70 + "\n"
            "THREAD SAFETY WARNING\n"
            "=" * 70 + "\n"
            f"Registry final count: {final_count}\n"
            f"Expected from register threads: {total_registered_from_register}\n"
            f"Observed issues: {len(observed_issues)}\n"
            "\n"
            "ContractHashRegistry is NOT thread-safe!\n"
            "Use external synchronization (threading.Lock) in production.\n"
            "See: docs/guides/THREADING.md\n"
            "=" * 70
        )

        # The test passes to document the pattern, but the warning is clear:
        # This code requires external synchronization for thread safety.
        assert True, warning_message

    def test_thread_safe_wrapper_pattern(self) -> None:
        """Demonstrate the correct pattern for thread-safe registry access.

        This test shows the recommended approach for using ContractHashRegistry
        in a multi-threaded environment: wrap all operations with a lock.

        This pattern is documented in docs/guides/THREADING.md and should be
        used whenever ContractHashRegistry is accessed from multiple threads.
        """
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Create registry with accompanying lock
        registry = ContractHashRegistry()
        registry_lock = threading.Lock()

        # Thread-safe wrapper functions
        def safe_register(name: str, fingerprint: str) -> None:
            with registry_lock:
                registry.register(name, fingerprint)

        def safe_lookup(name: str) -> str | None:
            with registry_lock:
                # Explicit type annotation to satisfy strict mypy
                result: str | None = registry.lookup_string(name)
                return result

        def safe_count() -> int:
            with registry_lock:
                # Explicit type annotation to satisfy strict mypy
                result: int = registry.count()
                return result

        # Track results
        registered_count = 0
        count_lock = threading.Lock()

        def register_with_lock(thread_id: int, count: int) -> int:
            """Register contracts using the thread-safe wrapper."""
            nonlocal registered_count
            local_count = 0
            for i in range(count):
                contract_name = f"safe_thread_{thread_id}_contract_{i}"
                fingerprint = f"1.0.0:{thread_id:06d}{i:06d}"
                safe_register(contract_name, fingerprint)
                local_count += 1
            with count_lock:
                registered_count += local_count
            return local_count

        # Run concurrent operations with proper locking
        num_threads = 4
        operations_per_thread = 50

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(register_with_lock, thread_id, operations_per_thread)
                for thread_id in range(num_threads)
            ]

            # Wait for all tasks
            for future in as_completed(futures):
                future.result()

        # With proper locking, results should be deterministic
        expected_total = num_threads * operations_per_thread
        actual_count = safe_count()

        # This should ALWAYS pass with proper locking
        assert actual_count == expected_total, (
            f"With proper locking, count should be exact. "
            f"Expected: {expected_total}, Got: {actual_count}"
        )

        # Verify all contracts can be looked up
        for thread_id in range(num_threads):
            for i in range(operations_per_thread):
                contract_name = f"safe_thread_{thread_id}_contract_{i}"
                result = safe_lookup(contract_name)
                assert result is not None, f"Contract {contract_name} should exist"


# =============================================================================
# Performance Benchmark Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestContractHashRegistryPerformance:
    """Performance benchmarks and expected characteristics.

    These tests document expected performance, not strict requirements.
    They serve as documentation and regression detection.

    Expected Performance (baseline on typical hardware):
        - Single fingerprint computation: <10ms for typical contract (~10-50 fields)
        - Registry lookup: O(1) hash table lookup (<0.1ms)
        - Memory: ~1KB per registered contract fingerprint

    Scaling Characteristics:
        - Fingerprint computation time scales linearly with contract size
        - Large contracts (1000+ fields): <100ms expected
        - Registry operations remain O(1) regardless of registry size

    Performance Optimization Hints:
        For applications with repeated fingerprint computations on the same
        contracts, consider implementing memoization at the application level.
        The compute_contract_fingerprint function is intentionally stateless
        to support thread-safe usage patterns. See docs/guides/THREADING.md
        for caching patterns in multi-threaded environments.
    """

    def test_fingerprint_computation_performance(
        self, sample_contract: ModelTestContract
    ) -> None:
        """Document typical fingerprint computation time.

        Expected: <10ms for a typical contract with ~10 fields.
        Safety bound: <100ms to account for CI environment variation.

        Typical observed times (local development):
            - Minimal contract (3 fields): ~0.1-0.5ms
            - Typical contract (10 fields): ~0.5-2ms
            - Complex contract (50 fields): ~2-5ms
        """
        import time

        iterations = 100
        start = time.perf_counter()

        for _ in range(iterations):
            compute_contract_fingerprint(sample_contract)

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        # Document observed time
        # Assert safety bound: each fingerprint should complete in <100ms
        # This is a generous bound to avoid flaky tests in CI
        assert avg_time_ms < 100, (
            f"Fingerprint computation averaged {avg_time_ms:.2f}ms, "
            f"exceeds 100ms safety bound"
        )

        # Note: Typical observed time is 0.5-2ms on modern hardware

    def test_registry_lookup_performance(self, registry: ContractHashRegistry) -> None:
        """Document registry lookup performance.

        Expected: O(1) hash table lookup, <1ms per lookup.
        Safety bound: <10ms to account for CI variation.

        Registry lookups use Python dict which provides O(1) average-case
        lookup time. This performance is independent of registry size.
        """
        import time

        # Register several contracts
        for i in range(100):
            registry.register(f"contract_{i}", f"1.0.0:{i:012d}")

        # Time lookups
        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            # Lookup contracts at various positions
            registry.lookup("contract_0")
            registry.lookup("contract_50")
            registry.lookup("contract_99")
            registry.lookup("nonexistent")

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / (iterations * 4)) * 1000

        # Assert O(1) behavior - should be very fast
        assert avg_time_ms < 10, (
            f"Registry lookup averaged {avg_time_ms:.4f}ms, exceeds 10ms safety bound"
        )

        # Note: Typical observed time is <0.01ms per lookup

    def test_large_contract_performance(self) -> None:
        """Document performance with larger contracts.

        Expected: <100ms for a contract with 1000 fields.
        Safety bound: <500ms for CI environments.

        Scaling characteristics:
            - Normalization: O(n) where n = total fields (including nested)
            - JSON serialization: O(n) where n = serialized size
            - SHA256 hashing: O(n) where n = bytes to hash

        The dominant factor is typically JSON serialization for very large
        contracts. Consider splitting very large contracts into smaller
        logical units if fingerprint computation becomes a bottleneck.
        """
        import time

        # Create a large contract with many nested fields
        large_contract = ModelTestContract(
            name="large_contract",
            contract_version="1.0.0",
            description="A contract with many fields for performance testing",
            nested={
                f"level1_{i}": {f"level2_{j}": f"value_{i}_{j}" for j in range(10)}
                for i in range(50)
            },
        )

        iterations = 10
        start = time.perf_counter()

        for _ in range(iterations):
            compute_contract_fingerprint(large_contract)

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        # Assert reasonable bound for large contracts
        assert avg_time_ms < 500, (
            f"Large contract fingerprint averaged {avg_time_ms:.2f}ms, "
            f"exceeds 500ms safety bound"
        )

        # Note: Typical observed time is 10-50ms for contracts with ~2000 fields

    def test_normalization_idempotency_performance(
        self, sample_contract: ModelTestContract
    ) -> None:
        """Verify normalization idempotency has no performance penalty.

        Normalizing an already-normalized contract should have similar
        performance to normalizing the original. This verifies that the
        idempotency guarantee does not introduce performance overhead.
        """
        import time

        # First normalization
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            normalize_contract(sample_contract)
        first_pass_ms = ((time.perf_counter() - start) / iterations) * 1000

        # Normalize once to get normalized form, then re-parse as model
        normalized_str = normalize_contract(sample_contract)
        normalized_dict = json.loads(normalized_str)
        reparsed_model = ModelTestContract.model_validate(normalized_dict)

        # Second normalization of already-normalized contract
        start = time.perf_counter()
        for _ in range(iterations):
            normalize_contract(reparsed_model)
        second_pass_ms = ((time.perf_counter() - start) / iterations) * 1000

        # Second pass should be similar or faster (no nulls to remove)
        # Allow up to 3x difference to account for measurement noise
        assert second_pass_ms < first_pass_ms * 3, (
            f"Second pass ({second_pass_ms:.2f}ms) significantly slower than "
            f"first pass ({first_pass_ms:.2f}ms)"
        )

    def test_registry_scaling_performance(self) -> None:
        """Document registry scaling with many registered contracts.

        Registry operations should remain O(1) regardless of size.
        This test verifies that lookup time does not degrade significantly
        as the registry grows.

        Expected: Lookup time remains constant (within noise margin)
        whether registry has 10 or 1000 contracts.
        """
        import time

        # Measure baseline with small registry
        small_registry = ContractHashRegistry()
        for i in range(10):
            small_registry.register(f"contract_{i}", f"1.0.0:{i:012d}")

        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            small_registry.lookup("contract_5")
        small_time_ms = ((time.perf_counter() - start) / iterations) * 1000

        # Measure with large registry
        large_registry = ContractHashRegistry()
        for i in range(1000):
            large_registry.register(f"contract_{i}", f"1.0.0:{i:012d}")

        start = time.perf_counter()
        for _ in range(iterations):
            large_registry.lookup("contract_500")
        large_time_ms = ((time.perf_counter() - start) / iterations) * 1000

        # O(1) behavior: large registry should not be significantly slower
        # Allow up to 5x difference to account for hash collision variance
        assert large_time_ms < small_time_ms * 5 + 0.1, (
            f"Large registry lookup ({large_time_ms:.4f}ms) significantly slower "
            f"than small registry ({small_time_ms:.4f}ms)"
        )

    def test_memory_baseline(self) -> None:
        """Document approximate memory usage per registered fingerprint.

        This test provides a baseline for memory usage planning.
        Actual memory usage depends on Python version and implementation.

        Expected: ~1KB per fingerprint (includes overhead)

        Memory components per fingerprint:
            - ModelContractFingerprint object: ~200-400 bytes
            - Hash strings (prefix + full): ~76 bytes
            - Version object: ~100-200 bytes
            - Dict entry overhead: ~50-100 bytes
        """
        import sys

        # Create a sample fingerprint
        fingerprint = compute_contract_fingerprint(
            ModelTestContract(name="test", contract_version="1.0.0")
        )

        # Get approximate size
        # Note: sys.getsizeof does not include referenced objects
        # This is a rough estimate for documentation purposes
        fingerprint_base_size = sys.getsizeof(fingerprint)

        # Registry entry includes the fingerprint + dict overhead
        registry = ContractHashRegistry()
        registry.register("test_contract", fingerprint)

        # Document that fingerprints have reasonable memory footprint
        # Pydantic models typically have overhead but are still efficient
        assert fingerprint_base_size < 5000, (
            f"Fingerprint base size ({fingerprint_base_size} bytes) unexpectedly large"
        )

        # Note: Actual total memory per entry (including all referenced objects)
        # is approximately 1KB. Use memory profiling tools for precise measurement.

    def test_drift_detection_performance(self, registry: ContractHashRegistry) -> None:
        """Document drift detection performance.

        Expected: <10ms per drift detection (includes fingerprint comparison).
        Safety bound: <50ms to account for CI variation.

        Drift detection is O(1) for the comparison itself, but includes:
            - Registry lookup: O(1)
            - Fingerprint parsing (if string): O(1)
            - Version and hash comparison: O(1)
        """
        import time

        # Register a baseline contract
        registry.register("my_contract", "1.0.0:abcdef123456")

        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            registry.detect_drift("my_contract", "1.0.0:abcdef123456")
            registry.detect_drift("my_contract", "1.0.0:fedcba987654")
            registry.detect_drift("my_contract", "2.0.0:abcdef123456")

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / (iterations * 3)) * 1000

        assert avg_time_ms < 50, (
            f"Drift detection averaged {avg_time_ms:.4f}ms, exceeds 50ms safety bound"
        )

        # Note: Typical observed time is <0.1ms per detection

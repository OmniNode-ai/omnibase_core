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

from omnibase_core.contracts import (
    ContractHashRegistry,
    ModelContractFingerprint,
    ModelContractNormalizationConfig,
    ModelDriftDetails,
    ModelDriftResult,
    compute_contract_fingerprint,
    normalize_contract,
)
from omnibase_core.models.contracts.model_contract_version import ModelContractVersion
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_contract() -> dict[str, object]:
    """Sample contract for testing."""
    return {
        "name": "test_contract",
        "version": "1.2.3",
        "description": "A test contract",
        "node_type": "COMPUTE",
        "input_model": "omnibase_core.models.ModelInput",
        "output_model": "omnibase_core.models.ModelOutput",
    }


@pytest.fixture
def sample_contract_with_nulls() -> dict[str, object]:
    """Sample contract with null values for testing null removal."""
    return {
        "name": "test_contract",
        "version": "1.0.0",
        "description": None,
        "optional_field": None,
        "nested": {
            "field_a": "value",
            "field_b": None,
            "deeply_nested": {
                "keep": "this",
                "remove": None,
            },
        },
        "list_with_nulls": [1, None, 3, None, 5],
    }


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

    def test_normalize_basic_contract(self, sample_contract: dict[str, object]) -> None:
        """Test basic contract normalization produces valid JSON."""
        result = normalize_contract(sample_contract)
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert parsed["name"] == "test_contract"

    def test_normalize_removes_null_values(
        self, sample_contract_with_nulls: dict[str, object]
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
        self, sample_contract_with_nulls: dict[str, object]
    ) -> None:
        """Test that null values are removed from lists."""
        result = normalize_contract(sample_contract_with_nulls)
        parsed = json.loads(result)

        # List should have nulls removed
        assert parsed["list_with_nulls"] == [1, 3, 5]

    def test_normalize_sorts_keys_alphabetically(self) -> None:
        """Test that keys are sorted alphabetically."""
        contract = {"zebra": 1, "apple": 2, "mango": 3}
        result = normalize_contract(contract)

        # Keys should appear in alphabetical order
        assert result == '{"apple":2,"mango":3,"zebra":1}'

    def test_normalize_sorts_nested_keys(self) -> None:
        """Test that nested keys are also sorted."""
        contract = {"outer": {"zebra": 1, "apple": 2}}
        result = normalize_contract(contract)

        # Nested keys should be sorted
        parsed = json.loads(result)
        nested_keys = list(parsed["outer"].keys())
        assert nested_keys == sorted(nested_keys)

    def test_normalize_compact_json_no_whitespace(
        self, sample_contract: dict[str, object]
    ) -> None:
        """Test that compact JSON has no extra whitespace."""
        result = normalize_contract(sample_contract)

        # Should not contain newlines or indentation spaces
        assert "\n" not in result
        assert "  " not in result

    def test_normalize_is_idempotent(self, sample_contract: dict[str, object]) -> None:
        """Test that normalize(normalize(c)) == normalize(c)."""
        first_pass = normalize_contract(sample_contract)
        # Parse and normalize again
        second_pass = normalize_contract(json.loads(first_pass))

        assert first_pass == second_pass

    def test_normalize_with_custom_config_no_null_removal(self) -> None:
        """Test normalization without null removal."""
        contract = {"name": "test", "optional": None}
        config = ModelContractNormalizationConfig(remove_nulls=False)

        result = normalize_contract(contract, config)
        parsed = json.loads(result)

        # Null should be preserved (as JSON null)
        assert "optional" in parsed
        assert parsed["optional"] is None

    def test_normalize_with_custom_config_no_sorting(self) -> None:
        """Test normalization without key sorting in local processing."""
        contract = {"zebra": 1, "apple": 2}
        config = ModelContractNormalizationConfig(sort_keys=False)

        result = normalize_contract(contract, config)
        # Note: json.dumps still uses sort_keys=True by default in normalize_contract
        # This tests the local canonical ordering step
        assert isinstance(result, str)

    def test_normalize_empty_contract(self) -> None:
        """Test normalizing an empty contract."""
        result = normalize_contract({})
        assert result == "{}"

    def test_normalize_deeply_nested_structure(self) -> None:
        """Test normalization of deeply nested structures."""
        contract = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "deep",
                        },
                    },
                },
            },
        }
        result = normalize_contract(contract)
        parsed = json.loads(result)
        assert parsed["level1"]["level2"]["level3"]["level4"]["value"] == "deep"


# =============================================================================
# Fingerprint Computation Tests
# =============================================================================


@pytest.mark.unit
class TestFingerprintComputation:
    """Tests for contract fingerprint computation."""

    def test_compute_fingerprint_basic(
        self, sample_contract: dict[str, object]
    ) -> None:
        """Test basic fingerprint computation."""
        fingerprint = compute_contract_fingerprint(sample_contract)

        assert isinstance(fingerprint, ModelContractFingerprint)
        assert fingerprint.version == ModelContractVersion.from_string("1.2.3")
        assert len(fingerprint.hash_prefix) == 12  # Default hash length
        assert len(fingerprint.full_hash) == 64  # Full SHA256

    def test_compute_fingerprint_format(
        self, sample_contract: dict[str, object]
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
        """Test that contracts without version default to 0.0.0."""
        contract = {"name": "test", "no_version": True}
        fingerprint = compute_contract_fingerprint(contract)

        assert fingerprint.version == ModelContractVersion(major=0, minor=0, patch=0)
        assert str(fingerprint).startswith("0.0.0:")

    def test_compute_fingerprint_with_dict_version(self) -> None:
        """Test fingerprint with version as dictionary."""
        contract = {
            "name": "test",
            "version": {"major": 2, "minor": 5, "patch": 1},
        }
        fingerprint = compute_contract_fingerprint(contract)

        assert fingerprint.version == ModelContractVersion(major=2, minor=5, patch=1)
        assert str(fingerprint).startswith("2.5.1:")

    def test_compute_fingerprint_with_model_version(self) -> None:
        """Test fingerprint with ModelContractVersion object."""
        version = ModelContractVersion(major=3, minor=0, patch=0)
        contract = {
            "name": "test",
            "version": version,
        }
        fingerprint = compute_contract_fingerprint(contract)

        assert fingerprint.version == version
        assert str(fingerprint).startswith("3.0.0:")

    def test_compute_fingerprint_deterministic(
        self, sample_contract: dict[str, object]
    ) -> None:
        """Test that fingerprint computation is deterministic."""
        fp1 = compute_contract_fingerprint(sample_contract)
        fp2 = compute_contract_fingerprint(sample_contract)

        assert str(fp1) == str(fp2)
        assert fp1.hash_prefix == fp2.hash_prefix
        assert fp1.full_hash == fp2.full_hash

    def test_compute_fingerprint_different_content_different_hash(self) -> None:
        """Test that different content produces different hashes."""
        contract1 = {"name": "test1", "version": "1.0.0"}
        contract2 = {"name": "test2", "version": "1.0.0"}

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        # Same version, different hash
        assert fp1.version == fp2.version
        assert fp1.hash_prefix != fp2.hash_prefix

    def test_compute_fingerprint_include_normalized_content(
        self, sample_contract: dict[str, object]
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
        self, sample_contract: dict[str, object]
    ) -> None:
        """Test custom hash length configuration."""
        config = ModelContractNormalizationConfig(hash_length=16)
        fingerprint = compute_contract_fingerprint(sample_contract, config)

        assert len(fingerprint.hash_prefix) == 16

    def test_compute_fingerprint_invalid_version_type_raises_error(self) -> None:
        """Test that invalid version type raises ModelOnexError."""
        contract = {"name": "test", "version": 123}  # Invalid type

        with pytest.raises(ModelOnexError) as exc_info:
            compute_contract_fingerprint(contract)

        assert "Invalid version type" in str(exc_info.value)


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
        self, registry: ContractHashRegistry, sample_contract: dict[str, object]
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
        self, registry: ContractHashRegistry, sample_contract: dict[str, object]
    ) -> None:
        """Test detect_drift_from_contract computes and detects drift."""
        # Register the original
        original_fp = registry.register_from_contract("my_contract", sample_contract)

        # Detect drift from same contract (should be no drift)
        result = registry.detect_drift_from_contract("my_contract", sample_contract)

        assert result.has_drift is False

        # Modify contract and detect drift
        modified_contract = dict(sample_contract)
        modified_contract["description"] = "Modified description"

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
        contract = {
            "name": "stability_test",
            "version": "1.0.0",
            "description": "Testing stability",
            "fields": ["a", "b", "c"],
        }

        # Compute multiple times
        fingerprints = [compute_contract_fingerprint(contract) for _ in range(10)]

        # All should be identical
        first = str(fingerprints[0])
        assert all(str(fp) == first for fp in fingerprints)

    def test_key_order_does_not_affect_fingerprint(self) -> None:
        """Test that key order doesn't affect fingerprint (canonical ordering)."""
        contract1 = {"zebra": 1, "apple": 2, "mango": 3, "version": "1.0.0"}
        contract2 = {"apple": 2, "mango": 3, "version": "1.0.0", "zebra": 1}

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        assert str(fp1) == str(fp2)

    def test_null_presence_normalized(self) -> None:
        """Test that null values are normalized consistently."""
        contract1 = {"name": "test", "version": "1.0.0", "optional": None}
        contract2 = {"name": "test", "version": "1.0.0"}  # No optional field

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        # Should be identical after null removal
        assert str(fp1) == str(fp2)

    def test_nested_null_removal_consistent(self) -> None:
        """Test that nested null removal is consistent."""
        contract1 = {
            "name": "test",
            "version": "1.0.0",
            "nested": {"keep": "value", "remove": None},
        }
        contract2 = {
            "name": "test",
            "version": "1.0.0",
            "nested": {"keep": "value"},
        }

        fp1 = compute_contract_fingerprint(contract1)
        fp2 = compute_contract_fingerprint(contract2)

        assert str(fp1) == str(fp2)

    def test_whitespace_normalization(self) -> None:
        """Test that whitespace in values is preserved but format is normalized."""
        contract = {
            "name": "  test  ",  # Whitespace in value
            "version": "1.0.0",
            "description": "line1\nline2",  # Newline in value
        }

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
        """Test that non-JSON-serializable content raises ModelOnexError."""
        contract = {"name": "test", "callback": lambda x: x}  # Lambda not serializable

        with pytest.raises(ModelOnexError) as exc_info:
            normalize_contract(contract)

        assert "Failed to normalize" in str(exc_info.value)

    def test_large_contract_normalization(self) -> None:
        """Test normalization of large contracts."""
        # Create a large contract
        large_contract = {
            "name": "large_contract",
            "version": "1.0.0",
            "fields": [f"field_{i}" for i in range(1000)],
            "nested": {f"key_{i}": f"value_{i}" for i in range(100)},
        }

        # Should complete without error
        fingerprint = compute_contract_fingerprint(large_contract)
        assert fingerprint is not None

    def test_special_characters_in_values(self) -> None:
        """Test handling of special characters in values."""
        contract = {
            "name": "test",
            "version": "1.0.0",
            "description": 'Contains "quotes" and \\backslashes\\ and \t tabs',
            "unicode": "Contains unicode: \u00e9\u00e8\u00ea",
        }

        # Should compute without error
        fingerprint = compute_contract_fingerprint(contract)
        assert fingerprint is not None

        # Should be deterministic
        fingerprint2 = compute_contract_fingerprint(contract)
        assert str(fingerprint) == str(fingerprint2)

    def test_empty_lists_preserved(self) -> None:
        """Test that empty lists are preserved in normalization."""
        contract = {"name": "test", "version": "1.0.0", "empty_list": []}

        result = normalize_contract(contract)
        parsed = json.loads(result)

        assert "empty_list" in parsed
        assert parsed["empty_list"] == []

    def test_empty_nested_dicts_removed_after_null_removal(self) -> None:
        """Test that empty dicts after null removal are also removed."""
        contract = {
            "name": "test",
            "version": "1.0.0",
            "nested": {"only_null": None},  # Will become empty after null removal
        }

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
        yaml_loaded = {
            "name": "my_service",
            "version": "1.0.0",
            "description": "Service contract",
            "optional_field": None,
            "node_type": "COMPUTE",
        }

        # Simulate loading from Python definition (no null fields)
        python_defined = {
            "name": "my_service",
            "version": "1.0.0",
            "description": "Service contract",
            "node_type": "COMPUTE",
        }

        fp_yaml = compute_contract_fingerprint(yaml_loaded)
        fp_python = compute_contract_fingerprint(python_defined)

        # Should produce identical fingerprints
        assert str(fp_yaml) == str(fp_python)

    def test_version_bump_detected_as_drift(self) -> None:
        """Test that version bump is detected as drift."""
        registry = ContractHashRegistry()

        # Register v1.0.0
        v1_contract = {"name": "my_service", "version": "1.0.0", "fields": ["a"]}
        registry.register_from_contract("my_service", v1_contract)

        # Check v1.1.0 with same content
        v1_1_contract = {"name": "my_service", "version": "1.1.0", "fields": ["a"]}

        result = registry.detect_drift_from_contract("my_service", v1_1_contract)

        assert result.has_drift is True
        assert result.drift_type == "both"  # Version and content changed

    def test_content_change_detected_as_drift(self) -> None:
        """Test that content changes are detected as drift."""
        registry = ContractHashRegistry()

        # Register original
        original = {"name": "my_service", "version": "1.0.0", "fields": ["a"]}
        registry.register_from_contract("my_service", original)

        # Check modified (same version, different content)
        modified = {"name": "my_service", "version": "1.0.0", "fields": ["a", "b"]}

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

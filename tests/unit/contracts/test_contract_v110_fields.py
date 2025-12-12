#!/usr/bin/env python3
"""
Unit Tests for Contract v1.1.0 Fields.

This module provides comprehensive validation tests for the v1.1.0 contract fields
introduced in the unified contract upgrade (OMN-258, OMN-259, OMN-260).

v1.1.0 Fields Tested:
    - fingerprint: Format "v{version}:{12-char-hash}" for drift detection
    - handlers: Required/optional handler specifications
    - profile_tags: Categorization tags list
    - subscriptions: Kafka topic subscriptions
    - contract_version consistency with fingerprint prefix

Related:
    - PR #161: v1.1.0 contract field validation
    - OMN-258, OMN-259, OMN-260: Unified contract upgrade tickets
"""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

# Import shared contract constants from test_runtime_contracts to avoid duplication
from tests.unit.contracts.test_runtime_contracts import (
    EXPECTED_RUNTIME_CONTRACTS,
    RUNTIME_CONTRACTS_DIR,
)

# Alias for v1.1.0 contracts (currently same as all runtime contracts)
V110_RUNTIME_CONTRACTS = EXPECTED_RUNTIME_CONTRACTS

# Path to example contracts directory
EXAMPLES_CONTRACTS_DIR = (
    Path(__file__).parent.parent.parent.parent / "examples" / "contracts"
)


def load_contract(contract_name: str) -> dict[str, Any]:
    """
    Load contract data from a YAML file.

    Args:
        contract_name: Name of the contract file (e.g., "runtime_orchestrator.yaml")

    Returns:
        Parsed YAML content as a dictionary

    Raises:
        pytest.fail: If the contract file does not exist, is empty, or is not a dict
    """
    contract_path = RUNTIME_CONTRACTS_DIR / contract_name
    if not contract_path.exists():
        pytest.fail(f"Contract file not found: {contract_path}")
    with open(contract_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if data is None:
            pytest.fail(f"Contract file is empty: {contract_path}")
        if not isinstance(data, dict):
            pytest.fail(f"Contract file is not a dict: {contract_path}")
        return data


# ==============================================================================
# Fingerprint Field Tests
# ==============================================================================


@pytest.mark.unit
class TestContractFingerprintField:
    """
    Tests for the v1.1.0 fingerprint field.

    The fingerprint field provides drift detection capability by combining
    the contract version with a hash prefix of the contract content.
    Format: "v{version}:{12-char-hash}" (e.g., "v1.1.0:8d00f09e22ec")
    """

    @pytest.fixture(params=V110_RUNTIME_CONTRACTS)
    def contract_name(self, request: pytest.FixtureRequest) -> str:
        """Parameterized fixture that yields each v1.1.0 contract name."""
        return request.param

    @pytest.fixture
    def contract_data(self, contract_name: str) -> dict:
        """Load and return contract data based on contract_name."""
        return load_contract(contract_name)

    def test_fingerprint_field_exists(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that v1.1.0 contracts have the fingerprint field."""
        assert "fingerprint" in contract_data, (
            f"{contract_name}: Missing v1.1.0 required field: fingerprint"
        )

    def test_fingerprint_is_string(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that fingerprint is a string."""
        fingerprint = contract_data.get("fingerprint")
        assert isinstance(fingerprint, str), (
            f"{contract_name}: fingerprint should be a string, got {type(fingerprint)}"
        )

    def test_fingerprint_format_version_colon_hash(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that fingerprint follows 'v{version}:{12-char-hash}' format."""
        fingerprint = contract_data.get("fingerprint", "")
        assert ":" in fingerprint, (
            f"{contract_name}: fingerprint should contain ':' separator, "
            f"got '{fingerprint}'"
        )

        parts = fingerprint.split(":", 1)
        assert len(parts) == 2, (
            f"{contract_name}: fingerprint should have exactly one ':' separator"
        )

        version_part, hash_part = parts
        assert version_part, f"{contract_name}: fingerprint version prefix is empty"
        assert hash_part, f"{contract_name}: fingerprint hash suffix is empty"
        assert version_part.startswith("v"), (
            f"{contract_name}: fingerprint version prefix should start with 'v', "
            f"got '{version_part}'"
        )

    def test_fingerprint_version_is_semver_format(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that fingerprint version prefix is valid semver format with v prefix."""
        fingerprint = contract_data.get("fingerprint", "")
        if ":" not in fingerprint:
            pytest.fail(
                f"{contract_name}: Invalid fingerprint format - no colon separator"
            )

        version_part = fingerprint.split(":", 1)[0]

        # Semver pattern with v prefix: vX.Y.Z
        semver_pattern = r"v\d+\.\d+\.\d+"
        assert re.fullmatch(semver_pattern, version_part), (
            f"{contract_name}: fingerprint version '{version_part}' "
            f"is not valid semver (expected vX.Y.Z format)"
        )

    def test_fingerprint_hash_is_12_lowercase_hex_characters(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that fingerprint hash suffix is 12 lowercase hexadecimal characters.

        Hash must be lowercase hex only (0-9a-f) for consistency and case-insensitive
        matching in downstream systems.
        """
        fingerprint = contract_data.get("fingerprint", "")
        if ":" not in fingerprint:
            pytest.fail(
                f"{contract_name}: Invalid fingerprint format - no colon separator"
            )

        hash_part = fingerprint.split(":", 1)[1]

        # Hash should be 12 lowercase hex characters only
        hex_pattern = r"[0-9a-f]{12}"
        assert re.fullmatch(hex_pattern, hash_part), (
            f"{contract_name}: fingerprint hash '{hash_part}' "
            f"should be exactly 12 lowercase hex characters (0-9a-f)"
        )

    def test_fingerprint_version_matches_contract_version(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that fingerprint version prefix matches contract_version field."""
        fingerprint = contract_data.get("fingerprint", "")
        contract_version = contract_data.get("contract_version", {})

        if ":" not in fingerprint:
            pytest.fail(
                f"{contract_name}: Invalid fingerprint format - no colon separator"
            )

        if not isinstance(contract_version, dict):
            pytest.fail(
                f"{contract_name}: contract_version is not a dict, "
                f"got {type(contract_version).__name__}"
            )

        fingerprint_version = fingerprint.split(":", 1)[0]
        # Expected format is v{major}.{minor}.{patch}
        expected_version = (
            f"v{contract_version.get('major', 0)}."
            f"{contract_version.get('minor', 0)}."
            f"{contract_version.get('patch', 0)}"
        )

        assert fingerprint_version == expected_version, (
            f"{contract_name}: fingerprint version '{fingerprint_version}' "
            f"does not match contract_version '{expected_version}'"
        )


# ==============================================================================
# Fingerprint Uniqueness Tests
# ==============================================================================


@pytest.mark.unit
class TestFingerprintUniqueness:
    """
    Tests to ensure fingerprint uniqueness across all contracts.

    Fingerprints must be unique to enable drift detection. Duplicate
    fingerprints defeat the purpose of the fingerprint field.
    """

    # Class-level references to module-level constants
    _RUNTIME_CONTRACTS_DIR = RUNTIME_CONTRACTS_DIR
    _EXAMPLES_CONTRACTS_DIR = EXAMPLES_CONTRACTS_DIR

    def _collect_all_fingerprints(self) -> dict[str, list[str]]:
        """
        Collect fingerprints from all contract files.

        Returns:
            Dictionary mapping fingerprint values to list of file paths that use them.
        """
        fingerprints: dict[str, list[str]] = {}  # fingerprint -> list of file paths

        # Collect from runtime contracts
        if self._RUNTIME_CONTRACTS_DIR.exists():
            for yaml_file in self._RUNTIME_CONTRACTS_DIR.glob("*.yaml"):
                try:
                    with open(yaml_file, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        # Guard: check data is not None before accessing
                        if data is None:
                            continue
                        if isinstance(data, dict) and "fingerprint" in data:
                            fp = data["fingerprint"]
                            if isinstance(fp, str):
                                fingerprints.setdefault(fp, []).append(
                                    str(yaml_file.name)
                                )
                except OSError:
                    # Skip file read errors gracefully
                    continue
                except yaml.YAMLError:
                    # Skip files with invalid YAML (will be caught by other tests)
                    continue

        # Collect from example contracts (recursive)
        if self._EXAMPLES_CONTRACTS_DIR.exists():
            for yaml_file in self._EXAMPLES_CONTRACTS_DIR.rglob("*.yaml"):
                try:
                    with open(yaml_file, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        # Guard: check data is not None before accessing
                        if data is None:
                            continue
                        if isinstance(data, dict) and "fingerprint" in data:
                            fp = data["fingerprint"]
                            if isinstance(fp, str):
                                rel_path = yaml_file.relative_to(
                                    self._EXAMPLES_CONTRACTS_DIR
                                )
                                fingerprints.setdefault(fp, []).append(
                                    f"examples/{rel_path}"
                                )
                except OSError:
                    # Skip file read errors gracefully
                    continue
                except yaml.YAMLError:
                    # Skip files with invalid YAML (will be caught by other tests)
                    continue

        return fingerprints

    def test_all_fingerprints_are_unique(self) -> None:
        """Test that no two contracts share the same fingerprint."""
        fingerprints = self._collect_all_fingerprints()

        duplicates = {fp: files for fp, files in fingerprints.items() if len(files) > 1}

        assert not duplicates, (
            "Fingerprint collision detected! The following fingerprints are used "
            "by multiple contracts:\n"
            + "\n".join(f"  {fp}: {files}" for fp, files in duplicates.items())
        )

    def test_minimum_contract_coverage(self) -> None:
        """Test that we're checking a reasonable number of contracts.

        This test ensures we have fingerprinted contracts in both expected locations:
        - contracts/runtime/ - Core runtime contracts (v1.1.0+)
        - examples/contracts/ - Example contracts demonstrating patterns

        The minimum count is tied to the V110_RUNTIME_CONTRACTS list rather than
        a magic number, making the test less brittle when contracts are added
        or removed.
        """
        fingerprints = self._collect_all_fingerprints()
        total_contracts = sum(len(files) for files in fingerprints.values())

        # Calculate expected minimum based on known contract directories
        expected_dirs = []
        if self._RUNTIME_CONTRACTS_DIR.exists():
            expected_dirs.append(("runtime", self._RUNTIME_CONTRACTS_DIR))
        if self._EXAMPLES_CONTRACTS_DIR.exists():
            expected_dirs.append(("examples", self._EXAMPLES_CONTRACTS_DIR))

        # We expect at least the number of v1.1.0 runtime contracts we explicitly test
        min_expected = (
            len(V110_RUNTIME_CONTRACTS) if self._RUNTIME_CONTRACTS_DIR.exists() else 0
        )

        assert total_contracts >= min_expected, (
            f"Expected at least {min_expected} contracts with fingerprints "
            f"(based on V110_RUNTIME_CONTRACTS list), found {total_contracts}. "
            f"Checked directories: {[name for name, _ in expected_dirs]}"
        )


# ==============================================================================
# Fingerprint Edge Cases Tests
# ==============================================================================


@pytest.mark.unit
class TestFingerprintEdgeCases:
    """
    Edge case tests for fingerprint validation.

    Tests malformed fingerprints, case sensitivity requirements, and
    determinism of fingerprint regeneration.
    """

    def test_fingerprint_format_validation_missing_colon(self) -> None:
        """Test that fingerprints without colon separator are detected as invalid."""
        invalid_fingerprint = "110abc123def456"  # No colon separator

        # Fingerprint must contain exactly one colon
        assert ":" not in invalid_fingerprint or invalid_fingerprint.count(":") != 1

    def test_fingerprint_format_validation_wrong_hash_length(self) -> None:
        """Test that fingerprints with wrong hash length are invalid."""
        # Hash is too short (8 chars instead of 12)
        short_hash_fingerprint = "v1.1.0:abc12345"
        parts = short_hash_fingerprint.split(":", 1)
        hash_part = parts[1] if len(parts) == 2 else ""

        hex_pattern = r"[0-9a-f]{12}"
        assert re.fullmatch(hex_pattern, hash_part) is None, (
            f"Short hash '{hash_part}' should not match 12-char hex pattern"
        )

        # Hash is too long (16 chars instead of 12)
        long_hash_fingerprint = "v1.1.0:abc123456789abcd"
        parts = long_hash_fingerprint.split(":", 1)
        hash_part = parts[1] if len(parts) == 2 else ""

        assert re.fullmatch(hex_pattern, hash_part) is None, (
            f"Long hash '{hash_part}' should not match 12-char hex pattern"
        )

    def test_fingerprint_hash_must_be_lowercase(self) -> None:
        """Test that uppercase hex characters in hash are invalid.

        Hash must be lowercase hex only (0-9a-f) for consistency.
        """
        # Uppercase hex should be rejected
        uppercase_fingerprint = "v1.1.0:ABC123DEF456"
        parts = uppercase_fingerprint.split(":", 1)
        hash_part = parts[1] if len(parts) == 2 else ""

        hex_pattern = r"[0-9a-f]{12}"
        assert re.fullmatch(hex_pattern, hash_part) is None, (
            f"Uppercase hash '{hash_part}' should not match lowercase hex pattern"
        )

    def test_fingerprint_hash_rejects_non_hex_characters(self) -> None:
        """Test that non-hex characters in hash are invalid."""
        # Contains 'g' which is not valid hex
        invalid_fingerprint = "v1.1.0:abc123ghijkl"
        parts = invalid_fingerprint.split(":", 1)
        hash_part = parts[1] if len(parts) == 2 else ""

        hex_pattern = r"[0-9a-f]{12}"
        assert re.fullmatch(hex_pattern, hash_part) is None, (
            f"Non-hex hash '{hash_part}' should not match hex pattern"
        )

    def test_valid_fingerprint_format_accepted(self) -> None:
        """Test that properly formatted fingerprints are accepted."""
        valid_fingerprint = "v1.1.0:8d00f09e22ec"
        parts = valid_fingerprint.split(":", 1)

        assert len(parts) == 2, "Fingerprint should split into exactly 2 parts"

        version_part, hash_part = parts

        # Version should be valid semver with v prefix
        semver_pattern = r"v\d+\.\d+\.\d+"
        assert re.fullmatch(semver_pattern, version_part), (
            f"Version '{version_part}' should be valid semver with v prefix"
        )

        # Hash should be 12 lowercase hex chars
        hex_pattern = r"[0-9a-f]{12}"
        assert re.fullmatch(hex_pattern, hash_part), (
            f"Hash '{hash_part}' should be 12 lowercase hex chars"
        )

    def test_fingerprint_determinism_same_content_same_hash(self) -> None:
        """Test that the same contract content produces the same fingerprint hash.

        Fingerprint generation must be deterministic - identical content should
        always produce identical hashes for drift detection to work correctly.
        """
        import hashlib

        # Sample contract content (simulating what would be hashed)
        contract_content = """
name: test_contract
version: 1.1.0
handlers:
  required: []
  optional: []
profile_tags:
  - test
"""
        # Hash should be deterministic
        hash1 = hashlib.sha256(contract_content.encode()).hexdigest()[:12]
        hash2 = hashlib.sha256(contract_content.encode()).hexdigest()[:12]

        assert hash1 == hash2, (
            "Same content should produce same hash prefix for deterministic fingerprints"
        )
        # Hash should be lowercase
        assert hash1 == hash1.lower(), "Hash should be lowercase"

    def test_fingerprint_different_content_different_hash(self) -> None:
        """Test that different contract content produces different fingerprint hashes.

        Even small changes in contract content should produce different hashes.
        """
        import hashlib

        content1 = "name: contract_a"
        content2 = "name: contract_b"

        hash1 = hashlib.sha256(content1.encode()).hexdigest()[:12]
        hash2 = hashlib.sha256(content2.encode()).hexdigest()[:12]

        assert hash1 != hash2, (
            "Different content should produce different hash prefixes"
        )


# ==============================================================================
# Handlers Field Tests
# ==============================================================================


@pytest.mark.unit
class TestContractHandlersField:
    """
    Tests for the v1.1.0 handlers field.

    The handlers field specifies required and optional handler dependencies
    that a node contract requires for execution.
    """

    @pytest.fixture(params=V110_RUNTIME_CONTRACTS)
    def contract_name(self, request: pytest.FixtureRequest) -> str:
        """Parameterized fixture that yields each v1.1.0 contract name."""
        return request.param

    @pytest.fixture
    def contract_data(self, contract_name: str) -> dict:
        """Load and return contract data based on contract_name."""
        return load_contract(contract_name)

    def test_handlers_field_exists(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that v1.1.0 contracts have the handlers field."""
        assert "handlers" in contract_data, (
            f"{contract_name}: Missing v1.1.0 required field: handlers"
        )

    def test_handlers_is_dict(self, contract_data: dict, contract_name: str) -> None:
        """Test that handlers is a dictionary."""
        handlers = contract_data.get("handlers")
        assert isinstance(handlers, dict), (
            f"{contract_name}: handlers should be a dict, got {type(handlers)}"
        )

    def test_handlers_has_required_key(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that handlers has 'required' key."""
        handlers = contract_data.get("handlers", {})
        assert "required" in handlers, (
            f"{contract_name}: handlers missing 'required' key"
        )

    def test_handlers_has_optional_key(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that handlers has 'optional' key."""
        handlers = contract_data.get("handlers", {})
        assert "optional" in handlers, (
            f"{contract_name}: handlers missing 'optional' key"
        )

    def test_handlers_required_is_list(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that handlers.required is a list."""
        handlers = contract_data.get("handlers", {})
        required = handlers.get("required")
        assert isinstance(required, list), (
            f"{contract_name}: handlers.required should be a list, got {type(required)}"
        )

    def test_handlers_optional_is_list(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that handlers.optional is a list."""
        handlers = contract_data.get("handlers", {})
        optional = handlers.get("optional")
        assert isinstance(optional, list), (
            f"{contract_name}: handlers.optional should be a list, got {type(optional)}"
        )

    def test_handler_entries_have_type_and_version(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that handler entries have 'type' and 'version' fields."""
        handlers = contract_data.get("handlers", {})

        # Early guard: ensure handlers is a dict before accessing .get()
        if not isinstance(handlers, dict):
            pytest.fail(
                f"{contract_name}: handlers should be a dict, "
                f"got {type(handlers).__name__}"
            )

        required = handlers.get("required", [])
        optional = handlers.get("optional", [])

        # Early guard: ensure required and optional are lists before iterating
        if not isinstance(required, list):
            pytest.fail(
                f"{contract_name}: handlers.required should be a list, "
                f"got {type(required).__name__}"
            )
        if not isinstance(optional, list):
            pytest.fail(
                f"{contract_name}: handlers.optional should be a list, "
                f"got {type(optional).__name__}"
            )

        for i, handler in enumerate(required):
            if not isinstance(handler, dict):
                pytest.fail(
                    f"{contract_name}: handlers.required[{i}] should be a dict, "
                    f"got {type(handler).__name__}: {handler}"
                )
            if "type" not in handler:
                pytest.fail(
                    f"{contract_name}: handlers.required[{i}] missing 'type' field"
                )
            if "version" not in handler:
                pytest.fail(
                    f"{contract_name}: handlers.required[{i}] missing 'version' field"
                )

        for i, handler in enumerate(optional):
            if not isinstance(handler, dict):
                pytest.fail(
                    f"{contract_name}: handlers.optional[{i}] should be a dict, "
                    f"got {type(handler).__name__}: {handler}"
                )
            if "type" not in handler:
                pytest.fail(
                    f"{contract_name}: handlers.optional[{i}] missing 'type' field"
                )
            if "version" not in handler:
                pytest.fail(
                    f"{contract_name}: handlers.optional[{i}] missing 'version' field"
                )


# ==============================================================================
# Profile Tags Field Tests
# ==============================================================================


@pytest.mark.unit
class TestContractProfileTagsField:
    """
    Tests for the v1.1.0 profile_tags field.

    The profile_tags field provides categorization tags for contract discovery
    and filtering.
    """

    @pytest.fixture(params=V110_RUNTIME_CONTRACTS)
    def contract_name(self, request: pytest.FixtureRequest) -> str:
        """Parameterized fixture that yields each v1.1.0 contract name."""
        return request.param

    @pytest.fixture
    def contract_data(self, contract_name: str) -> dict:
        """Load and return contract data based on contract_name."""
        return load_contract(contract_name)

    def test_profile_tags_field_exists(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that v1.1.0 contracts have the profile_tags field."""
        assert "profile_tags" in contract_data, (
            f"{contract_name}: Missing v1.1.0 required field: profile_tags"
        )

    def test_profile_tags_is_list(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that profile_tags is a list."""
        profile_tags = contract_data.get("profile_tags")
        assert isinstance(profile_tags, list), (
            f"{contract_name}: profile_tags should be a list, got {type(profile_tags)}"
        )

    def test_profile_tags_not_empty(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that profile_tags is not empty."""
        profile_tags = contract_data.get("profile_tags", [])
        assert len(profile_tags) > 0, (
            f"{contract_name}: profile_tags should not be empty"
        )

    def test_profile_tags_all_strings(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that all profile_tags are strings."""
        profile_tags = contract_data.get("profile_tags", [])
        for i, tag in enumerate(profile_tags):
            assert isinstance(tag, str), (
                f"{contract_name}: profile_tags[{i}] should be a string, "
                f"got {type(tag)}: {tag}"
            )

    def test_profile_tags_no_empty_strings(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that no profile_tags are empty strings."""
        profile_tags = contract_data.get("profile_tags", [])
        for i, tag in enumerate(profile_tags):
            if isinstance(tag, str):
                assert tag.strip(), (
                    f"{contract_name}: profile_tags[{i}] is empty or whitespace"
                )

    def test_profile_tags_no_duplicates(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that profile_tags has no duplicates."""
        profile_tags = contract_data.get("profile_tags", [])
        unique_tags = set(profile_tags)
        assert len(unique_tags) == len(profile_tags), (
            f"{contract_name}: profile_tags contains duplicates"
        )

    def test_profile_tags_include_runtime(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that runtime contracts include 'runtime' tag."""
        profile_tags = contract_data.get("profile_tags", [])
        assert "runtime" in profile_tags, (
            f"{contract_name}: runtime contract should have 'runtime' tag"
        )


# ==============================================================================
# Subscriptions Field Tests
# ==============================================================================


@pytest.mark.unit
class TestContractSubscriptionsField:
    """
    Tests for the v1.1.0 subscriptions field.

    The subscriptions field defines Kafka topic subscriptions for event-driven
    contracts.
    """

    # Only test contracts that should have subscriptions
    CONTRACTS_WITH_SUBSCRIPTIONS = [
        "contract_loader_effect.yaml",
        "event_bus_wiring_effect.yaml",
    ]

    @pytest.fixture(params=CONTRACTS_WITH_SUBSCRIPTIONS)
    def contract_name(self, request: pytest.FixtureRequest) -> str:
        """Parameterized fixture that yields contracts with subscriptions."""
        return request.param

    @pytest.fixture
    def contract_data(self, contract_name: str) -> dict:
        """Load and return contract data based on contract_name."""
        return load_contract(contract_name)

    def test_subscriptions_field_exists(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that effect contracts have the subscriptions field."""
        assert "subscriptions" in contract_data, (
            f"{contract_name}: Missing v1.1.0 field: subscriptions"
        )

    def test_subscriptions_structure(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that subscriptions has valid structure."""
        subscriptions = contract_data.get("subscriptions")

        # Subscriptions can be a dict with 'topics' key or a list
        if isinstance(subscriptions, dict):
            assert "topics" in subscriptions, (
                f"{contract_name}: subscriptions dict missing 'topics' key"
            )
            topics = subscriptions.get("topics", [])
            assert isinstance(topics, list), (
                f"{contract_name}: subscriptions.topics should be a list"
            )
        elif isinstance(subscriptions, list):
            # List format is also valid (list of subscription objects)
            pass
        else:
            pytest.fail(
                f"{contract_name}: subscriptions should be dict or list, "
                f"got {type(subscriptions)}"
            )


@pytest.mark.unit
class TestContractSubscriptionsTopicsFormat:
    """
    Tests for subscriptions.topics format validation.

    Only tests contracts that have explicit topics field in subscriptions.
    """

    def test_contract_loader_effect_subscriptions_topics_is_list(self) -> None:
        """Test contract_loader_effect subscriptions.topics is a list (may be empty)."""
        contract_data = load_contract("contract_loader_effect.yaml")
        subscriptions = contract_data.get("subscriptions", {})

        if isinstance(subscriptions, dict):
            topics = subscriptions.get("topics", [])
            assert isinstance(topics, list), (
                "contract_loader_effect: subscriptions.topics should be a list"
            )
        # If subscriptions is a list, that's also valid

    def test_event_bus_wiring_effect_subscriptions_has_topics(self) -> None:
        """Test event_bus_wiring_effect has subscriptions with topics.

        This contract can have subscriptions in two formats:
        1. Dict format with 'topics' key containing list of topic dicts
        2. List format with subscription objects directly

        Topics should follow the 'onex.*' naming convention.
        """
        contract_data = load_contract("event_bus_wiring_effect.yaml")
        subscriptions = contract_data.get("subscriptions", {})

        # Determine the topics list based on format
        topics: list[Any] = []
        if isinstance(subscriptions, dict):
            topics = subscriptions.get("topics", [])
            assert isinstance(topics, list), (
                "event_bus_wiring_effect: subscriptions.topics should be a list"
            )
        elif isinstance(subscriptions, list):
            # List format - subscriptions is directly a list of topic entries
            topics = subscriptions
        else:
            pytest.fail(
                f"event_bus_wiring_effect: subscriptions should be dict or list, "
                f"got {type(subscriptions).__name__}"
            )

        # This contract should have actual topic subscriptions
        assert len(topics) > 0, (
            "event_bus_wiring_effect: subscriptions.topics should not be empty"
        )

        # Validate each topic entry
        for i, topic in enumerate(topics):
            if isinstance(topic, str):
                # String topics should not be empty and follow naming convention
                assert topic.strip(), (
                    f"event_bus_wiring_effect: subscriptions.topics[{i}] "
                    f"is empty string"
                )
                assert topic.startswith("onex."), (
                    f"event_bus_wiring_effect: subscriptions.topics[{i}] "
                    f"should follow 'onex.*' naming convention, got '{topic}'"
                )
            elif isinstance(topic, dict):
                # Dict topics should have a topic identifier
                topic_name = topic.get("topic", topic.get("name", ""))
                assert topic_name, (
                    f"event_bus_wiring_effect: subscriptions.topics[{i}] "
                    f"dict entry missing 'topic' or 'name' field"
                )
                assert isinstance(topic_name, str), (
                    f"event_bus_wiring_effect: subscriptions.topics[{i}].topic "
                    f"should be a string, got {type(topic_name).__name__}"
                )
                assert topic_name.startswith("onex."), (
                    f"event_bus_wiring_effect: subscriptions.topics[{i}] "
                    f"should follow 'onex.*' naming convention, got '{topic_name}'"
                )
            else:
                pytest.fail(
                    f"event_bus_wiring_effect: subscriptions.topics[{i}] "
                    f"should be str or dict, got {type(topic).__name__}"
                )


@pytest.mark.unit
class TestSubscriptionsElementShape:
    """
    Tests for subscription element shape validation.

    Validates that individual subscription entries have the expected structure
    when subscriptions contains object entries (not just string topic names).
    """

    # Only test contracts that have subscriptions with topic objects
    CONTRACTS_WITH_SUBSCRIPTIONS = [
        "event_bus_wiring_effect.yaml",
    ]

    @pytest.fixture(params=CONTRACTS_WITH_SUBSCRIPTIONS)
    def contract_name(self, request: pytest.FixtureRequest) -> str:
        """Parameterized fixture for contracts with subscriptions."""
        return request.param

    @pytest.fixture
    def contract_data(self, contract_name: str) -> dict[str, Any]:
        """Load and return contract data based on contract_name."""
        return load_contract(contract_name)

    def test_subscription_topic_entries_are_valid_type(
        self, contract_data: dict[str, Any], contract_name: str
    ) -> None:
        """Test that subscription topic entries are strings or dicts.

        Topics can be either:
        - Simple strings (topic names)
        - Dicts with topic configuration (name, filter, handler, etc.)
        """
        subscriptions = contract_data.get("subscriptions", {})

        topics: list[Any] = []
        if isinstance(subscriptions, dict):
            topics = subscriptions.get("topics", [])
        elif isinstance(subscriptions, list):
            topics = subscriptions

        if not isinstance(topics, list):
            pytest.fail(
                f"{contract_name}: subscriptions.topics should be a list, "
                f"got {type(topics).__name__}"
            )

        for i, topic in enumerate(topics):
            if not isinstance(topic, (str, dict)):
                pytest.fail(
                    f"{contract_name}: subscriptions.topics[{i}] should be str or dict, "
                    f"got {type(topic).__name__}: {topic}"
                )

    def test_subscription_dict_entries_have_required_fields(
        self, contract_data: dict[str, Any], contract_name: str
    ) -> None:
        """Test that dict subscription entries have minimal required fields.

        When topics are objects (dicts), they should have at least a 'topic' or 'name'
        field to identify the Kafka topic.
        """
        subscriptions = contract_data.get("subscriptions", {})

        # Use Any type to allow defensive isinstance check
        topics: Any = []
        if isinstance(subscriptions, dict):
            topics = subscriptions.get("topics", [])
        elif isinstance(subscriptions, list):
            topics = subscriptions

        if not isinstance(topics, list):
            return  # Already covered by other test

        for i, topic in enumerate(topics):
            if isinstance(topic, dict):
                # Dict entries should have topic name in some form
                has_topic_name = (
                    "topic" in topic
                    or "name" in topic
                    or "topic_name" in topic
                    or "pattern" in topic  # Some systems use pattern matching
                )
                assert has_topic_name, (
                    f"{contract_name}: subscriptions.topics[{i}] dict entry "
                    f"missing topic identifier (expected 'topic', 'name', 'topic_name', "
                    f"or 'pattern' key). Got keys: {list(topic.keys())}"
                )

    def test_subscription_strings_are_not_empty(
        self, contract_data: dict[str, Any], contract_name: str
    ) -> None:
        """Test that string subscription entries are not empty."""
        subscriptions = contract_data.get("subscriptions", {})

        # Use Any type to allow defensive isinstance check
        topics: Any = []
        if isinstance(subscriptions, dict):
            topics = subscriptions.get("topics", [])
        elif isinstance(subscriptions, list):
            topics = subscriptions

        if not isinstance(topics, list):
            return  # Already covered by other test

        for i, topic in enumerate(topics):
            if isinstance(topic, str):
                assert topic.strip(), (
                    f"{contract_name}: subscriptions.topics[{i}] is empty string"
                )

    def test_subscription_topics_follow_naming_convention(
        self, contract_data: dict[str, Any], contract_name: str
    ) -> None:
        """Test that subscription topics follow the 'onex.*' naming convention.

        All ONEX event topics should start with 'onex.' prefix to:
        - Prevent namespace collisions with external systems
        - Enable clear identification of ONEX internal events
        - Support wildcard filtering in event bus configurations
        """
        subscriptions = contract_data.get("subscriptions", {})

        # Use Any type to allow defensive isinstance check
        topics: Any = []
        if isinstance(subscriptions, dict):
            topics = subscriptions.get("topics", [])
        elif isinstance(subscriptions, list):
            topics = subscriptions

        if not isinstance(topics, list):
            return  # Already covered by other test

        for i, topic in enumerate(topics):
            topic_name: str | None = None
            if isinstance(topic, str):
                topic_name = topic
            elif isinstance(topic, dict):
                topic_name = topic.get("topic", topic.get("name", ""))

            if topic_name and isinstance(topic_name, str) and topic_name.strip():
                assert topic_name.startswith("onex."), (
                    f"{contract_name}: subscriptions.topics[{i}] should follow "
                    f"'onex.*' naming convention, got '{topic_name}'"
                )

    def test_list_format_subscriptions_have_required_fields(
        self, contract_data: dict[str, Any], contract_name: str
    ) -> None:
        """Test that list format subscriptions have required fields.

        When subscriptions is a list (not dict with topics key), each entry
        should be a dict with at least 'topic' field and preferably a 'handler'
        or 'description' for documentation.
        """
        subscriptions = contract_data.get("subscriptions")

        # Only validate list format subscriptions
        if not isinstance(subscriptions, list):
            return  # Skip dict format (validated by other tests)

        for i, entry in enumerate(subscriptions):
            if not isinstance(entry, dict):
                pytest.fail(
                    f"{contract_name}: subscriptions[{i}] in list format "
                    f"should be a dict, got {type(entry).__name__}"
                )

            # Must have topic identifier
            has_topic = "topic" in entry or "name" in entry or "pattern" in entry
            assert has_topic, (
                f"{contract_name}: subscriptions[{i}] missing topic identifier "
                f"(expected 'topic', 'name', or 'pattern' key). "
                f"Got keys: {list(entry.keys())}"
            )

            # Topic value must be a non-empty string
            topic_value = entry.get("topic", entry.get("name", entry.get("pattern")))
            if topic_value is not None:
                assert isinstance(topic_value, str), (
                    f"{contract_name}: subscriptions[{i}].topic should be a string, "
                    f"got {type(topic_value).__name__}"
                )
                assert topic_value.strip(), (
                    f"{contract_name}: subscriptions[{i}].topic is empty"
                )


# ==============================================================================
# Contract Version Consistency Tests
# ==============================================================================


@pytest.mark.unit
class TestContractVersionConsistency:
    """
    Tests for contract version field consistency.

    Ensures contract_version dict values match expected v1.1.0 format
    and are consistent across the contract.
    """

    @pytest.fixture(params=V110_RUNTIME_CONTRACTS)
    def contract_name(self, request: pytest.FixtureRequest) -> str:
        """Parameterized fixture that yields each v1.1.0 contract name."""
        return request.param

    @pytest.fixture
    def contract_data(self, contract_name: str) -> dict:
        """Load and return contract data based on contract_name."""
        return load_contract(contract_name)

    def test_contract_version_is_v110(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that contract_version is v1.1.0."""
        version = contract_data.get("contract_version", {})
        assert isinstance(version, dict), (
            f"{contract_name}: contract_version should be dict"
        )
        assert version.get("major") == 1, (
            f"{contract_name}: contract_version.major should be 1"
        )
        assert version.get("minor") == 1, (
            f"{contract_name}: contract_version.minor should be 1"
        )
        assert version.get("patch") == 0, (
            f"{contract_name}: contract_version.patch should be 0"
        )

    def test_contract_version_values_are_integers(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that contract_version values are integers."""
        version = contract_data.get("contract_version", {})
        if isinstance(version, dict):
            assert isinstance(version.get("major"), int), (
                f"{contract_name}: contract_version.major should be int"
            )
            assert isinstance(version.get("minor"), int), (
                f"{contract_name}: contract_version.minor should be int"
            )
            assert isinstance(version.get("patch"), int), (
                f"{contract_name}: contract_version.patch should be int"
            )


# ==============================================================================
# All v1.1.0 Fields Present Tests
# ==============================================================================


@pytest.mark.unit
class TestAllV110FieldsPresent:
    """
    Aggregate test to ensure all v1.1.0 required fields are present.
    """

    # EFFECT contracts require subscriptions field (even if empty)
    EFFECT_CONTRACTS = [
        "contract_loader_effect.yaml",
        "event_bus_wiring_effect.yaml",
    ]

    @pytest.fixture(params=V110_RUNTIME_CONTRACTS)
    def contract_name(self, request: pytest.FixtureRequest) -> str:
        """Parameterized fixture that yields each v1.1.0 contract name."""
        return request.param

    @pytest.fixture
    def contract_data(self, contract_name: str) -> dict:
        """Load and return contract data based on contract_name."""
        return load_contract(contract_name)

    def test_all_v110_fields_present(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that all v1.1.0 required fields are present."""
        required_fields = ["fingerprint", "handlers", "profile_tags"]

        # EFFECT contracts require subscriptions field
        if contract_name in self.EFFECT_CONTRACTS:
            required_fields.append("subscriptions")

        missing_fields = []
        for field in required_fields:
            if field not in contract_data:
                missing_fields.append(field)

        assert not missing_fields, (
            f"{contract_name}: Missing v1.1.0 required fields: {missing_fields}"
        )


# ==============================================================================
# Example Contracts Tests (if any exist)
# ==============================================================================


@pytest.mark.unit
class TestExampleContractsV110Compliance:
    """
    Tests for v1.1.0 compliance in example contracts directory.

    Only runs if example contracts exist with v1.1.0 fields.
    """

    EXAMPLES_DIR = Path(__file__).parent.parent.parent.parent / "examples" / "contracts"

    def test_examples_directory_exists(self) -> None:
        """Test that examples/contracts directory exists."""
        # This is informational - examples may not always exist
        if not self.EXAMPLES_DIR.exists():
            pytest.skip("examples/contracts directory does not exist")

    def test_example_contracts_have_valid_yaml(self) -> None:
        """Test that example contracts are valid YAML."""
        if not self.EXAMPLES_DIR.exists():
            pytest.skip("examples/contracts directory does not exist")

        yaml_files = list(self.EXAMPLES_DIR.rglob("*.yaml"))
        if not yaml_files:
            pytest.skip("No example contracts found")

        for yaml_file in yaml_files:
            with open(yaml_file, encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    assert data is not None, f"{yaml_file.name}: Empty YAML"
                except yaml.YAMLError as e:
                    pytest.fail(f"{yaml_file.name}: Invalid YAML - {e}")

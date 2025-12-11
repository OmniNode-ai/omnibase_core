#!/usr/bin/env python3
"""
Unit Tests for Contract v1.1.0 Fields.

This module provides comprehensive validation tests for the v1.1.0 contract fields
introduced in the unified contract upgrade (OMN-258, OMN-259, OMN-260).

v1.1.0 Fields Tested:
    - fingerprint: Format "version:hash-prefix" for drift detection
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

import pytest
import yaml

# Path to the runtime contracts directory
RUNTIME_CONTRACTS_DIR = (
    Path(__file__).parent.parent.parent.parent / "contracts" / "runtime"
)

# v1.1.0 runtime contracts
V110_RUNTIME_CONTRACTS = [
    "runtime_orchestrator.yaml",
    "contract_loader_effect.yaml",
    "contract_registry_reducer.yaml",
    "node_graph_reducer.yaml",
    "event_bus_wiring_effect.yaml",
]


def load_contract(contract_name: str) -> dict[str, object]:
    """
    Load contract data from a YAML file.

    Args:
        contract_name: Name of the contract file (e.g., "runtime_orchestrator.yaml")

    Returns:
        Parsed YAML content as a dictionary

    Raises:
        pytest.skip: If the contract file does not exist or is empty
    """
    contract_path = RUNTIME_CONTRACTS_DIR / contract_name
    if not contract_path.exists():
        pytest.skip(f"Contract file not found: {contract_path}")
    with open(contract_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if data is None:
            pytest.skip(f"Contract file is empty: {contract_path}")
        if not isinstance(data, dict):
            pytest.skip(f"Contract file is not a dict: {contract_path}")
        return dict(data)


# ==============================================================================
# Fingerprint Field Tests
# ==============================================================================


@pytest.mark.unit
class TestContractFingerprintField:
    """
    Tests for the v1.1.0 fingerprint field.

    The fingerprint field provides drift detection capability by combining
    the contract version with a hash prefix of the contract content.
    Format: "version:hash-prefix" (e.g., "1.1.0:8d00f09e22ec")
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
        """Test that fingerprint follows 'version:hash-prefix' format."""
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

    def test_fingerprint_version_is_semver_format(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that fingerprint version prefix is valid semver format."""
        fingerprint = contract_data.get("fingerprint", "")
        if ":" not in fingerprint:
            pytest.skip("Invalid fingerprint format - no colon separator")

        version_part = fingerprint.split(":", 1)[0]

        # Semver pattern: major.minor.patch
        semver_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(semver_pattern, version_part), (
            f"{contract_name}: fingerprint version '{version_part}' "
            f"is not valid semver (expected X.Y.Z format)"
        )

    def test_fingerprint_hash_is_12_hex_characters(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that fingerprint hash suffix is 12 hexadecimal characters."""
        fingerprint = contract_data.get("fingerprint", "")
        if ":" not in fingerprint:
            pytest.skip("Invalid fingerprint format - no colon separator")

        hash_part = fingerprint.split(":", 1)[1]

        # Hash should be 12 hex characters
        hex_pattern = r"^[0-9a-fA-F]{12}$"
        assert re.match(hex_pattern, hash_part), (
            f"{contract_name}: fingerprint hash '{hash_part}' "
            f"should be exactly 12 hex characters"
        )

    def test_fingerprint_version_matches_contract_version(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that fingerprint version prefix matches contract_version field."""
        fingerprint = contract_data.get("fingerprint", "")
        contract_version = contract_data.get("contract_version", {})

        if ":" not in fingerprint:
            pytest.skip("Invalid fingerprint format - no colon separator")

        if not isinstance(contract_version, dict):
            pytest.skip("contract_version is not a dict")

        fingerprint_version = fingerprint.split(":", 1)[0]
        expected_version = (
            f"{contract_version.get('major', 0)}."
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

    RUNTIME_CONTRACTS_DIR = (
        Path(__file__).parent.parent.parent.parent / "contracts" / "runtime"
    )
    EXAMPLES_CONTRACTS_DIR = (
        Path(__file__).parent.parent.parent.parent / "examples" / "contracts"
    )

    def _collect_all_fingerprints(self) -> dict[str, list[str]]:
        """
        Collect fingerprints from all contract files.

        Returns:
            Dictionary mapping fingerprint values to list of file paths that use them.
        """
        fingerprints: dict[str, list[str]] = {}  # fingerprint -> list of file paths

        # Collect from runtime contracts
        if self.RUNTIME_CONTRACTS_DIR.exists():
            for yaml_file in self.RUNTIME_CONTRACTS_DIR.glob("*.yaml"):
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict) and "fingerprint" in data:
                        fp = data["fingerprint"]
                        fingerprints.setdefault(fp, []).append(str(yaml_file.name))

        # Collect from example contracts (recursive)
        if self.EXAMPLES_CONTRACTS_DIR.exists():
            for yaml_file in self.EXAMPLES_CONTRACTS_DIR.rglob("*.yaml"):
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict) and "fingerprint" in data:
                        fp = data["fingerprint"]
                        rel_path = yaml_file.relative_to(self.EXAMPLES_CONTRACTS_DIR)
                        fingerprints.setdefault(fp, []).append(f"examples/{rel_path}")

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
        """Test that we're checking a reasonable number of contracts."""
        fingerprints = self._collect_all_fingerprints()
        total_contracts = sum(len(files) for files in fingerprints.values())

        # We expect at least 10 contracts with fingerprints
        assert total_contracts >= 10, (
            f"Expected at least 10 contracts with fingerprints, found {total_contracts}"
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
        required = handlers.get("required", [])
        optional = handlers.get("optional", [])

        for i, handler in enumerate(required):
            if not isinstance(handler, dict):
                continue
            assert "type" in handler, (
                f"{contract_name}: handlers.required[{i}] missing 'type' field"
            )
            assert "version" in handler, (
                f"{contract_name}: handlers.required[{i}] missing 'version' field"
            )

        for i, handler in enumerate(optional):
            if not isinstance(handler, dict):
                continue
            assert "type" in handler, (
                f"{contract_name}: handlers.optional[{i}] missing 'type' field"
            )
            assert "version" in handler, (
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
        """Test event_bus_wiring_effect has subscriptions with topics."""
        contract_data = load_contract("event_bus_wiring_effect.yaml")
        subscriptions = contract_data.get("subscriptions", {})

        # event_bus_wiring_effect uses dict format with topics
        if isinstance(subscriptions, dict):
            topics = subscriptions.get("topics", [])
            assert isinstance(topics, list), (
                "event_bus_wiring_effect: subscriptions.topics should be a list"
            )
            # This contract should have actual topic subscriptions
            assert len(topics) > 0, (
                "event_bus_wiring_effect: subscriptions.topics should not be empty"
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

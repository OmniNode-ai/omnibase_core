# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for contract loader with !include directive support.

This module tests the IncludeLoader and load_contract functionality
for loading YAML contracts with !include directives.

See Also:
    OMN-1047: YAML !include directive support implementation
"""

from pathlib import Path

import pytest

from omnibase_core.contracts.contract_loader import (
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_MAX_INCLUDE_DEPTH,
    IncludeLoader,
    load_contract,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.fixture
def fixtures_path() -> Path:
    """Return the path to test fixtures."""
    return Path(__file__).parent / "fixtures"


@pytest.mark.unit
class TestContractLoaderBasic:
    """Tests for basic contract loading without includes."""

    def test_load_simple_contract(self, fixtures_path: Path) -> None:
        """Test loading a simple contract without includes."""
        contract = load_contract(fixtures_path / "basic_contract.yaml")

        assert contract["node_name"] == "test_node"
        assert contract["node_type"] == "COMPUTE_GENERIC"
        assert contract["contract_version"]["major"] == 1

    def test_load_empty_file_returns_empty_dict(self, fixtures_path: Path) -> None:
        """Test that empty files return an empty dictionary."""
        contract = load_contract(fixtures_path / "subcontracts" / "empty.yaml")
        assert contract == {}

    def test_file_not_found_raises_error(self, fixtures_path: Path) -> None:
        """Test that missing files raise ModelOnexError with FILE_NOT_FOUND."""
        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(fixtures_path / "nonexistent.yaml")

        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_non_dict_contract_raises_error(self, tmp_path: Path) -> None:
        """Test that non-dict YAML raises ModelOnexError."""
        # Create a YAML file with a list instead of dict
        yaml_file = tmp_path / "list_contract.yaml"
        yaml_file.write_text("- item1\n- item2\n")

        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(yaml_file)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "mapping" in str(exc_info.value.message).lower()


@pytest.mark.unit
class TestContractLoaderWithIncludes:
    """Tests for contract loading with !include directives."""

    def test_single_include(self, fixtures_path: Path) -> None:
        """Test loading a contract with a single !include directive."""
        contract = load_contract(fixtures_path / "contract_with_include.yaml")

        assert contract["node_name"] == "orchestrator_node"
        assert "routing" in contract
        assert contract["routing"]["default_handler"] == "main"
        assert len(contract["routing"]["routes"]) == 2

    def test_multiple_includes(self, fixtures_path: Path) -> None:
        """Test loading a contract with multiple !include directives."""
        contract = load_contract(fixtures_path / "contract_multiple_includes.yaml")

        assert contract["node_name"] == "multi_include_node"
        assert "routing" in contract
        assert "events" in contract
        assert contract["routing"]["default_handler"] == "main"
        assert len(contract["events"]["consumed"]) == 2

    def test_nested_includes(self, fixtures_path: Path) -> None:
        """Test loading a contract with nested includes (A includes B, B includes C)."""
        contract = load_contract(fixtures_path / "nested_include.yaml")

        assert contract["node_name"] == "nested_node"
        assert contract["config"]["name"] == "level1"
        assert contract["config"]["nested"]["name"] == "level2"
        assert contract["config"]["nested"]["value"] == 42

    def test_empty_include_returns_none(self, fixtures_path: Path) -> None:
        """Test that including an empty file results in None value."""
        contract = load_contract(fixtures_path / "empty_include.yaml")

        assert contract["name"] == "with_empty"
        assert contract["ref"] is None


@pytest.mark.unit
class TestContractLoaderCircularDetection:
    """Tests for circular include detection."""

    def test_circular_include_detection(self, fixtures_path: Path) -> None:
        """Test that circular includes (A -> B -> A) are detected."""
        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(fixtures_path / "circular_a.yaml")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "circular" in str(exc_info.value.message).lower()

    def test_self_reference_detection(self, fixtures_path: Path) -> None:
        """Test that self-referential includes (A -> A) are detected."""
        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(fixtures_path / "self_reference.yaml")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        # Self-reference is detected as circular
        assert "circular" in str(exc_info.value.message).lower()


@pytest.mark.unit
class TestContractLoaderSecurity:
    """Tests for security features."""

    def test_path_traversal_blocked(self, fixtures_path: Path) -> None:
        """Test that path traversal attempts (../) are blocked."""
        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(fixtures_path / "path_traversal.yaml")

        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION

    def test_absolute_path_blocked(self, fixtures_path: Path) -> None:
        """Test that absolute paths are blocked."""
        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(fixtures_path / "absolute_path.yaml")

        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION

    def test_missing_include_raises_not_found(self, fixtures_path: Path) -> None:
        """Test that missing include files raise FILE_NOT_FOUND error."""
        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(fixtures_path / "missing_include.yaml")

        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND


@pytest.mark.unit
class TestContractLoaderDepthLimit:
    """Tests for include depth limiting."""

    def test_max_depth_exceeded(self, tmp_path: Path) -> None:
        """Test that maximum include depth is enforced."""
        # Create a chain of includes that exceeds the depth limit
        # This creates: main -> level0 -> level1 -> ... -> level10 -> level11
        subcontracts = tmp_path / "subcontracts"
        subcontracts.mkdir()

        # Create main contract
        main_contract = tmp_path / "main.yaml"
        main_contract.write_text("config: !include subcontracts/level0.yaml\n")

        # Create chain of includes deeper than DEFAULT_MAX_INCLUDE_DEPTH
        for i in range(DEFAULT_MAX_INCLUDE_DEPTH + 2):
            level_file = subcontracts / f"level{i}.yaml"
            next_level = i + 1
            level_file.write_text(
                f"name: level{i}\nnested: !include level{next_level}.yaml\n"
            )

        # Create final level without include
        final_level = subcontracts / f"level{DEFAULT_MAX_INCLUDE_DEPTH + 2}.yaml"
        final_level.write_text("name: final\n")

        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(main_contract)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "depth" in str(exc_info.value.message).lower()


@pytest.mark.unit
class TestContractLoaderFileSizeLimit:
    """Tests for file size limiting."""

    def test_file_too_large(self, tmp_path: Path) -> None:
        """Test that files exceeding size limit are rejected."""
        large_file = tmp_path / "large.yaml"
        # Create file larger than default max (1MB)
        large_content = "data: " + "x" * (DEFAULT_MAX_FILE_SIZE + 100)
        large_file.write_text(large_content)

        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(large_file)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "large" in str(exc_info.value.message).lower()

    def test_custom_max_file_size(self, tmp_path: Path) -> None:
        """Test that custom max_file_size is respected."""
        small_file = tmp_path / "small.yaml"
        small_file.write_text("data: " + "x" * 1000)  # ~1KB

        # Should fail with 500 byte limit
        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(small_file, max_file_size=500)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


@pytest.mark.unit
class TestContractLoaderCustomOptions:
    """Tests for custom loader options."""

    def test_custom_max_depth(self, tmp_path: Path) -> None:
        """Test that custom max_depth is respected."""
        subcontracts = tmp_path / "subcontracts"
        subcontracts.mkdir()

        main_contract = tmp_path / "main.yaml"
        main_contract.write_text("config: !include subcontracts/level0.yaml\n")

        level0 = subcontracts / "level0.yaml"
        level0.write_text("nested: !include level1.yaml\n")

        level1 = subcontracts / "level1.yaml"
        level1.write_text("nested: !include level2.yaml\n")

        level2 = subcontracts / "level2.yaml"
        level2.write_text("value: final\n")

        # Should fail with max_depth=2
        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(main_contract, max_depth=2)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "depth" in str(exc_info.value.message).lower()

        # Should succeed with max_depth=3
        contract = load_contract(main_contract, max_depth=3)
        assert contract["config"]["nested"]["nested"]["value"] == "final"


@pytest.mark.unit
class TestIncludeLoaderClass:
    """Tests for IncludeLoader class directly."""

    def test_include_loader_inherits_safe_loader(self) -> None:
        """Test that IncludeLoader inherits from yaml.SafeLoader."""
        import yaml

        assert issubclass(IncludeLoader, yaml.SafeLoader)

    def test_include_constructor_registered(self) -> None:
        """Test that !include constructor is registered."""

        # Check that !include tag is registered
        assert "!include" in IncludeLoader.yaml_constructors


@pytest.mark.unit
class TestContractLoaderEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_include_with_special_characters_in_filename(self, tmp_path: Path) -> None:
        """Test including files with special characters in names."""
        subcontracts = tmp_path / "subcontracts"
        subcontracts.mkdir()

        # Create file with spaces and underscores
        special_file = subcontracts / "routing_config.yaml"
        special_file.write_text("handler: main\n")

        main_contract = tmp_path / "main.yaml"
        main_contract.write_text("routing: !include subcontracts/routing_config.yaml\n")

        contract = load_contract(main_contract)
        assert contract["routing"]["handler"] == "main"

    def test_include_yaml_with_comments(self, tmp_path: Path) -> None:
        """Test that YAML comments in included files are handled."""
        subcontracts = tmp_path / "subcontracts"
        subcontracts.mkdir()

        commented_file = subcontracts / "commented.yaml"
        commented_file.write_text("# This is a comment\nvalue: 42  # inline comment\n")

        main_contract = tmp_path / "main.yaml"
        main_contract.write_text("config: !include subcontracts/commented.yaml\n")

        contract = load_contract(main_contract)
        assert contract["config"]["value"] == 42

    def test_include_scalar_value(self, tmp_path: Path) -> None:
        """Test including a file that contains a scalar value."""
        subcontracts = tmp_path / "subcontracts"
        subcontracts.mkdir()

        scalar_file = subcontracts / "version.yaml"
        scalar_file.write_text('"1.0.0"\n')

        main_contract = tmp_path / "main.yaml"
        main_contract.write_text("version: !include subcontracts/version.yaml\n")

        contract = load_contract(main_contract)
        assert contract["version"] == "1.0.0"

    def test_include_list_value(self, tmp_path: Path) -> None:
        """Test including a file that contains a list."""
        subcontracts = tmp_path / "subcontracts"
        subcontracts.mkdir()

        list_file = subcontracts / "items.yaml"
        list_file.write_text("- item1\n- item2\n- item3\n")

        main_contract = tmp_path / "main.yaml"
        main_contract.write_text("items: !include subcontracts/items.yaml\n")

        contract = load_contract(main_contract)
        assert contract["items"] == ["item1", "item2", "item3"]


@pytest.mark.unit
class TestContractLoaderDefaults:
    """Tests for default configuration values."""

    def test_default_max_include_depth(self) -> None:
        """Test that DEFAULT_MAX_INCLUDE_DEPTH is reasonable."""
        assert DEFAULT_MAX_INCLUDE_DEPTH == 10
        assert DEFAULT_MAX_INCLUDE_DEPTH > 0

    def test_default_max_file_size(self) -> None:
        """Test that DEFAULT_MAX_FILE_SIZE is reasonable."""
        assert DEFAULT_MAX_FILE_SIZE == 1024 * 1024  # 1MB
        assert DEFAULT_MAX_FILE_SIZE > 0

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strict duplicate mapping key coverage for contract loading and includes."""

import inspect
from pathlib import Path

import pytest

import omnibase_core.contracts.contract_loader as contract_loader
from omnibase_core.contracts.contract_loader import IncludeLoader, load_contract
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_duplicate_yaml_mapping_key import (
    DuplicateYamlMappingKeyError,
)
from omnibase_core.errors.model_onex_error import ModelOnexError

SOURCE_ROOT = Path(__file__).parents[3] / "src"
CONTRACT_PATHS = sorted((SOURCE_ROOT / "omnibase_core").rglob("contract.yaml"))


@pytest.mark.unit
class TestContractLoaderDuplicateKeys:
    """Reject duplicates consistently across string, file, and include loading."""

    def test_top_level_duplicate(self, tmp_path: Path) -> None:
        """Direct string parsing reports the repeated key and its second line."""
        loader = IncludeLoader(
            "node_name: first\nnode_name: second\n", base_path=tmp_path
        )
        try:
            with pytest.raises(DuplicateYamlMappingKeyError) as exc_info:
                loader.get_single_data()
        finally:
            loader.dispose()

        error = exc_info.value
        assert error.key == "node_name"
        assert error.line == 2
        assert error.source == "<contract>"
        assert "duplicate key 'node_name'" in str(error)
        assert "<contract>:2:" in str(error)

    def test_nested_duplicate(self, tmp_path: Path) -> None:
        """Nested mappings use the same strict construction as the root."""
        loader = IncludeLoader(
            "routing:\n  handler: first\n  handler: second\n",
            base_path=tmp_path,
            source="nested.yaml",
        )
        try:
            with pytest.raises(DuplicateYamlMappingKeyError) as exc_info:
                loader.get_single_data()
        finally:
            loader.dispose()

        error = exc_info.value
        assert error.key == "handler"
        assert error.line == 3
        assert error.source == "nested.yaml"
        assert "duplicate key 'handler'" in str(error)
        assert "nested.yaml:3:" in str(error)

    def test_include_duplicate(self, tmp_path: Path) -> None:
        """Included file failures retain the include path, key, and line."""
        include_path = tmp_path / "sub.yaml"
        include_path.write_text("handler: first\nhandler: second\n", encoding="utf-8")
        loader = IncludeLoader("routing: !include sub.yaml", base_path=tmp_path)
        try:
            with pytest.raises(ModelOnexError) as exc_info:
                loader.get_single_data()
        finally:
            loader.dispose()

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR
        assert "Invalid YAML in include file" in error.message
        assert "duplicate key 'handler'" in error.message
        assert f"{include_path.resolve()}:2:" in error.message

    def test_file_duplicate(self, tmp_path: Path) -> None:
        """File parsing wraps duplicates as configuration parse errors."""
        contract_path = tmp_path / "contract.yaml"
        contract_path.write_text(
            "node_name: first\nnode_name: second\n", encoding="utf-8"
        )

        with pytest.raises(ModelOnexError) as exc_info:
            load_contract(contract_path)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR
        assert "Invalid YAML in contract file" in error.message
        assert "duplicate key 'node_name'" in error.message
        assert f"{contract_path.resolve()}:2:" in error.message

    def test_valid_string_and_file_parity(self, tmp_path: Path) -> None:
        """Identical valid contract text produces identical mappings."""
        content = (
            "node_name: example\n"
            "contract_version:\n  major: 1\n  minor: 0\n  patch: 0\n"
            "routing: !include sub.yaml\n"
        )
        contract_path = tmp_path / "contract.yaml"
        contract_path.write_text(content, encoding="utf-8")
        (tmp_path / "sub.yaml").write_text("handler: main\n", encoding="utf-8")
        loader = IncludeLoader(content, base_path=tmp_path)
        try:
            from_string = loader.get_single_data()
        finally:
            loader.dispose()

        assert (
            from_string
            == load_contract(contract_path)
            == {
                "node_name": "example",
                "contract_version": {"major": 1, "minor": 0, "patch": 0},
                "routing": {"handler": "main"},
            }
        )

    def test_duplicate_string_and_file_parity(self, tmp_path: Path) -> None:
        """Wrapped file failures preserve the string parser's key and line."""
        content = "node_name: first\nnode_name: second\n"
        contract_path = tmp_path / "contract.yaml"
        contract_path.write_text(content, encoding="utf-8")
        loader = IncludeLoader(content, base_path=tmp_path)
        try:
            with pytest.raises(DuplicateYamlMappingKeyError) as string_exc:
                loader.get_single_data()
        finally:
            loader.dispose()

        with pytest.raises(ModelOnexError) as file_exc:
            load_contract(contract_path)

        cause = file_exc.value.__cause__
        assert isinstance(cause, DuplicateYamlMappingKeyError)
        assert cause.key == string_exc.value.key == "node_name"
        assert cause.line == string_exc.value.line == 2
        assert cause.source == str(contract_path.resolve())

    def test_merge_override_duplicate(self, tmp_path: Path) -> None:
        """Merge precedence cannot silently override an inherited key."""
        loader = IncludeLoader(
            "base: &base\n  handler: first\nrouting:\n  <<: *base\n  handler: second\n",
            base_path=tmp_path,
        )
        try:
            with pytest.raises(DuplicateYamlMappingKeyError) as exc_info:
                loader.get_single_data()
        finally:
            loader.dispose()

        error = exc_info.value
        assert error.key == "handler"
        assert error.line == 5
        assert "duplicate key 'handler'" in str(error)
        assert "<contract>:5:" in str(error)

    def test_merge_without_duplicate(self, tmp_path: Path) -> None:
        """Merges with distinct keys still expand into ordinary mappings."""
        loader = IncludeLoader(
            "base: &base\n  handler: main\nrouting:\n  <<: *base\n  retries: 3\n",
            base_path=tmp_path,
        )
        try:
            result = loader.get_single_data()
        finally:
            loader.dispose()

        assert result == {
            "base": {"handler": "main"},
            "routing": {"handler": "main", "retries": 3},
        }

    def test_loader_has_no_environment_reads(self) -> None:
        """Loader behavior has no environment-variable configuration."""
        source = inspect.getsource(contract_loader)
        assert "os.environ" not in source
        assert "getenv" not in source


@pytest.mark.unit
class TestRealContractCompatibility:
    """Keep every shipped contract loadable under duplicate rejection."""

    def test_contract_discovery_is_nonempty(self) -> None:
        """The compatibility check must exercise at least one real contract."""
        assert CONTRACT_PATHS, f"No contract.yaml files found under {SOURCE_ROOT}"

    @pytest.mark.parametrize(
        "contract_path",
        CONTRACT_PATHS,
        ids=[str(path.relative_to(SOURCE_ROOT)) for path in CONTRACT_PATHS],
    )
    def test_real_contract_loads(self, contract_path: Path) -> None:
        """Each real contract parses to a mapping without duplicate keys."""
        assert isinstance(load_contract(contract_path), dict), str(contract_path)

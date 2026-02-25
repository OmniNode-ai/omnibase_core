# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for validator_startup_contract.py (OMN-1533).

Verifies acceptance criteria:
- Server logs warning if contract.yaml is missing
- Server logs confirmation when contract.yaml is found
- Does not block startup (no exceptions raised)
- Basic YAML parsing validation when contract is found
"""

from pathlib import Path

import pytest

from omnibase_core.validation.validator_startup_contract import (
    StartupContractValidationResult,
    validate_startup_contract,
)


@pytest.mark.unit
class TestValidateStartupContractMissing:
    """contract.yaml does not exist at the given path."""

    def test_returns_not_found(self, tmp_path: Path) -> None:
        path = tmp_path / "contract.yaml"
        result = validate_startup_contract(path)
        assert result.found is False

    def test_valid_yaml_false_when_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "contract.yaml"
        result = validate_startup_contract(path)
        assert result.valid_yaml is False

    def test_contract_data_none_when_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "contract.yaml"
        result = validate_startup_contract(path)
        assert result.contract_data is None

    def test_warning_message_present_when_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "contract.yaml"
        result = validate_startup_contract(path)
        assert result.warning_message is not None
        assert len(result.warning_message) > 0

    def test_does_not_raise(self, tmp_path: Path) -> None:
        """Startup must never be blocked by missing contract."""
        path = tmp_path / "nonexistent" / "contract.yaml"
        # Must not raise even with deeply missing path
        result = validate_startup_contract(path)
        assert isinstance(result, StartupContractValidationResult)

    def test_path_is_directory_not_file(self, tmp_path: Path) -> None:
        """When path exists but is a directory, found=False."""
        dir_path = tmp_path / "contract.yaml"
        dir_path.mkdir()
        result = validate_startup_contract(dir_path)
        assert result.found is False
        assert result.warning_message is not None


@pytest.mark.unit
class TestValidateStartupContractFound:
    """contract.yaml exists and is valid YAML."""

    def _write_contract(self, tmp_path: Path, content: str) -> Path:
        path = tmp_path / "contract.yaml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_returns_found_true(self, tmp_path: Path) -> None:
        path = self._write_contract(
            tmp_path,
            "name: TestNode\ncontract_version:\n  major: 1\n  minor: 0\n  patch: 0\n",
        )
        result = validate_startup_contract(path)
        assert result.found is True

    def test_returns_valid_yaml_true(self, tmp_path: Path) -> None:
        path = self._write_contract(
            tmp_path,
            "name: TestNode\nnode_type: compute\n",
        )
        result = validate_startup_contract(path)
        assert result.valid_yaml is True

    def test_contract_data_populated(self, tmp_path: Path) -> None:
        path = self._write_contract(
            tmp_path,
            "name: TestNode\nnode_type: compute\n",
        )
        result = validate_startup_contract(path)
        assert result.contract_data is not None
        assert result.contract_data["name"] == "TestNode"
        assert result.contract_data["node_type"] == "compute"

    def test_no_warning_message_on_success(self, tmp_path: Path) -> None:
        path = self._write_contract(
            tmp_path,
            "name: TestNode\nnode_type: effect\n",
        )
        result = validate_startup_contract(path)
        assert result.warning_message is None

    def test_node_name_accepted(self, tmp_path: Path) -> None:
        """node_name parameter flows through without error."""
        path = self._write_contract(tmp_path, "name: MyNode\n")
        result = validate_startup_contract(path, node_name="MyNode")
        assert result.found is True

    def test_minimal_valid_yaml(self, tmp_path: Path) -> None:
        """Single-key YAML is valid."""
        path = self._write_contract(tmp_path, "key: value\n")
        result = validate_startup_contract(path)
        assert result.found is True
        assert result.valid_yaml is True
        assert result.contract_data == {"key": "value"}


@pytest.mark.unit
class TestValidateStartupContractMalformedYaml:
    """contract.yaml exists but contains invalid YAML syntax."""

    def test_found_true_but_valid_yaml_false(self, tmp_path: Path) -> None:
        path = tmp_path / "contract.yaml"
        path.write_text("key: [unclosed\n", encoding="utf-8")
        result = validate_startup_contract(path)
        assert result.found is True
        assert result.valid_yaml is False

    def test_contract_data_none_on_parse_error(self, tmp_path: Path) -> None:
        path = tmp_path / "contract.yaml"
        path.write_text("key: [unclosed\n", encoding="utf-8")
        result = validate_startup_contract(path)
        assert result.contract_data is None

    def test_warning_message_on_parse_error(self, tmp_path: Path) -> None:
        path = tmp_path / "contract.yaml"
        path.write_text("key: [unclosed\n", encoding="utf-8")
        result = validate_startup_contract(path)
        assert result.warning_message is not None

    def test_does_not_raise_on_malformed_yaml(self, tmp_path: Path) -> None:
        """Startup must never be blocked by malformed contract."""
        path = tmp_path / "contract.yaml"
        path.write_text("{{bad: yaml: {{{\n", encoding="utf-8")
        # Must not raise
        result = validate_startup_contract(path)
        assert isinstance(result, StartupContractValidationResult)

    def test_non_mapping_top_level(self, tmp_path: Path) -> None:
        """YAML that parses but is not a mapping (e.g., a list)."""
        path = tmp_path / "contract.yaml"
        path.write_text("- item1\n- item2\n", encoding="utf-8")
        result = validate_startup_contract(path)
        assert result.found is True
        assert result.valid_yaml is False
        assert result.contract_data is None
        assert result.warning_message is not None

    def test_scalar_top_level(self, tmp_path: Path) -> None:
        """YAML that parses to a plain string, not a mapping."""
        path = tmp_path / "contract.yaml"
        path.write_text("just a string\n", encoding="utf-8")
        result = validate_startup_contract(path)
        assert result.found is True
        assert result.valid_yaml is False


@pytest.mark.unit
class TestValidateStartupContractResultType:
    """StartupContractValidationResult is a NamedTuple with correct fields."""

    def test_result_is_named_tuple(self, tmp_path: Path) -> None:
        path = tmp_path / "contract.yaml"
        result = validate_startup_contract(path)
        assert hasattr(result, "found")
        assert hasattr(result, "valid_yaml")
        assert hasattr(result, "contract_data")
        assert hasattr(result, "warning_message")

    def test_result_immutable(self, tmp_path: Path) -> None:
        path = tmp_path / "contract.yaml"
        result = validate_startup_contract(path)
        with pytest.raises(AttributeError):
            result.found = True  # type: ignore[misc]

    def test_can_construct_directly(self) -> None:
        result = StartupContractValidationResult(
            found=True,
            valid_yaml=True,
            contract_data={"name": "test"},
            warning_message=None,
        )
        assert result.found is True
        assert result.contract_data == {"name": "test"}


@pytest.mark.unit
class TestValidateStartupContractOversizedFile:
    """File exceeding the 1 MB size limit produces a warning."""

    def test_oversized_file_found_true_valid_yaml_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from omnibase_core.validation import validator_startup_contract as vsc

        monkeypatch.setattr(vsc, "_MAX_CONTRACT_SIZE_BYTES", 10)
        path = tmp_path / "contract.yaml"
        path.write_text("name: TestNode\nnode_type: compute\n", encoding="utf-8")
        result = validate_startup_contract(path)
        assert result.found is True
        assert result.valid_yaml is False
        assert result.warning_message is not None

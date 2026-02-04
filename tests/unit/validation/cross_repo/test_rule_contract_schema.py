"""Tests for contract_schema_valid rule.

Related ticket: OMN-1775
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleContractSchemaConfig,
)
from omnibase_core.validation.cross_repo.rules.rule_contract_schema import (
    RuleContractSchema,
)

if TYPE_CHECKING:
    from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
        ModelFileImports,
    )


class TestRuleContractSchema:
    """Tests for RuleContractSchema."""

    @pytest.fixture
    def config(self) -> ModelRuleContractSchemaConfig:
        """Create a test configuration."""
        return ModelRuleContractSchemaConfig(
            enabled=True,
            severity=EnumSeverity.ERROR,
            required_fields=["contract_version", "node_type", "name", "description"],
            deprecated_fields={"version": "Use 'contract_version' instead"},
            contract_directories=["contracts/"],
        )

    @pytest.fixture
    def tmp_contracts_dir(self, tmp_path: Path) -> Path:
        """Create a temporary contracts directory."""
        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir()
        return contracts_dir

    def test_detects_missing_required_field(
        self,
        config: ModelRuleContractSchemaConfig,
        tmp_path: Path,
        tmp_contracts_dir: Path,
    ) -> None:
        """Test that missing required fields are detected."""
        # Create a contract missing 'description'
        contract_file = tmp_contracts_dir / "bad_contract.yaml"
        contract_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
name: my_node
# missing description
"""
        )

        rule = RuleContractSchema(config)
        file_imports: dict[Path, ModelFileImports] = {}

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].code == "CONTRACT_SCHEMA_MISSING_FIELD"
        assert "description" in issues[0].message

    def test_detects_deprecated_version_field(
        self,
        config: ModelRuleContractSchemaConfig,
        tmp_path: Path,
        tmp_contracts_dir: Path,
    ) -> None:
        """Test that deprecated 'version' field is detected."""
        contract_file = tmp_contracts_dir / "deprecated_contract.yaml"
        contract_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
version: "1.0.0"  # deprecated
node_type: COMPUTE_GENERIC
name: my_node
description: Test node
"""
        )

        rule = RuleContractSchema(config)
        file_imports: dict[Path, ModelFileImports] = {}

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Should have one warning for deprecated field
        deprecated_issues = [
            i for i in issues if i.code == "CONTRACT_SCHEMA_DEPRECATED_FIELD"
        ]
        assert len(deprecated_issues) == 1
        assert deprecated_issues[0].severity == EnumSeverity.WARNING
        assert "version" in deprecated_issues[0].message

    def test_passes_valid_contract(
        self,
        config: ModelRuleContractSchemaConfig,
        tmp_path: Path,
        tmp_contracts_dir: Path,
    ) -> None:
        """Test that valid contracts pass without issues."""
        contract_file = tmp_contracts_dir / "good_contract.yaml"
        contract_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
name: my_node
description: A valid test node
"""
        )

        rule = RuleContractSchema(config)
        file_imports: dict[Path, ModelFileImports] = {}

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_detects_invalid_yaml(
        self,
        config: ModelRuleContractSchemaConfig,
        tmp_path: Path,
        tmp_contracts_dir: Path,
    ) -> None:
        """Test that invalid YAML is detected."""
        contract_file = tmp_contracts_dir / "invalid.yaml"
        contract_file.write_text(
            """
contract_version:
  major: 1
  - this is invalid yaml
    with bad indentation
"""
        )

        rule = RuleContractSchema(config)
        file_imports: dict[Path, ModelFileImports] = {}

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].code == "CONTRACT_SCHEMA_INVALID_YAML"

    def test_skips_when_disabled(
        self,
        tmp_path: Path,
        tmp_contracts_dir: Path,
    ) -> None:
        """Test that rule is skipped when disabled."""
        config = ModelRuleContractSchemaConfig(enabled=False)

        contract_file = tmp_contracts_dir / "bad_contract.yaml"
        contract_file.write_text("invalid: true")  # Missing required fields

        rule = RuleContractSchema(config)
        file_imports: dict[Path, ModelFileImports] = {}

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_handles_non_dict_yaml(
        self,
        config: ModelRuleContractSchemaConfig,
        tmp_path: Path,
        tmp_contracts_dir: Path,
    ) -> None:
        """Test that non-dict YAML content is detected."""
        contract_file = tmp_contracts_dir / "scalar.yaml"
        contract_file.write_text("just a string")

        rule = RuleContractSchema(config)
        file_imports: dict[Path, ModelFileImports] = {}

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].code == "CONTRACT_SCHEMA_INVALID_YAML"
        assert "mapping" in issues[0].message.lower()

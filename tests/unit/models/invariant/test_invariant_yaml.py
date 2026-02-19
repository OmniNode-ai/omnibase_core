# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for YAML parsing of invariant definitions."""

from pathlib import Path

import pytest

from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.invariant import (
    load_invariant_set_from_file,
    load_invariant_sets_from_directory,
    parse_invariant_set_from_yaml,
)


@pytest.mark.unit
class TestYamlParsing:
    """Test YAML parsing functionality."""

    def test_parse_invariant_set_from_yaml(self) -> None:
        """Valid YAML produces correct InvariantSet."""
        yaml_content = """
name: "Model Output Validation"
target: "node_llm_call"
invariants:
  - name: "Response has required fields"
    type: field_presence
    severity: critical
    config:
      fields: ["response", "model"]
  - name: "Latency under 5s"
    type: latency
    severity: warning
    config:
      max_ms: 5000
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        assert inv_set.name == "Model Output Validation"
        assert inv_set.target == "node_llm_call"
        assert len(inv_set.invariants) == 2

    def test_yaml_parsing_validates_invariant_types(self) -> None:
        """Invalid type in YAML raises clear error."""
        yaml_content = """
name: "Test"
target: "node_test"
invariants:
  - name: "Invalid"
    type: invalid_type
    config: {}
"""
        with pytest.raises((ModelOnexError, ValueError)):
            parse_invariant_set_from_yaml(yaml_content)

    def test_yaml_supports_all_invariant_types(self) -> None:
        """Each invariant type can be defined in YAML with proper configs."""
        # Each type requires specific config keys in YAML format
        type_configs = {
            EnumInvariantType.SCHEMA: 'json_schema: {"type": "object"}',
            EnumInvariantType.FIELD_PRESENCE: 'fields: ["response"]',
            EnumInvariantType.FIELD_VALUE: 'field_path: "status"',
            EnumInvariantType.THRESHOLD: 'metric_name: "accuracy"',
            EnumInvariantType.LATENCY: "max_ms: 5000",
            EnumInvariantType.COST: "max_cost: 0.10",
            EnumInvariantType.CUSTOM: 'callable_path: "my_module.validator"',
        }
        for inv_type in EnumInvariantType:
            config_yaml = type_configs[inv_type]
            yaml_content = f"""
name: "Test {inv_type.value}"
target: "node_test"
invariants:
  - name: "{inv_type.value} test"
    type: {inv_type.value}
    config:
      {config_yaml}
"""
            inv_set = parse_invariant_set_from_yaml(yaml_content)
            assert inv_set.invariants[0].type == inv_type

    def test_yaml_parses_all_severity_levels(self) -> None:
        """All severity levels can be defined in YAML."""
        for severity in EnumSeverity:
            yaml_content = f"""
name: "Test Severity"
target: "node_test"
invariants:
  - name: "Severity test"
    type: latency
    severity: {severity.value}
    config:
      max_ms: 5000
"""
            inv_set = parse_invariant_set_from_yaml(yaml_content)
            assert inv_set.invariants[0].severity == severity

    def test_yaml_with_description(self) -> None:
        """YAML with description field."""
        yaml_content = """
name: "Described Set"
target: "node_llm_call"
description: "A comprehensive validation set for LLM calls"
invariants:
  - name: "Latency check"
    type: latency
    description: "Ensure response time is acceptable"
    config:
      max_ms: 5000
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        assert inv_set.description == "A comprehensive validation set for LLM calls"
        assert inv_set.invariants[0].description == "Ensure response time is acceptable"

    def test_yaml_with_enabled_flag(self) -> None:
        """YAML with enabled flag on invariants."""
        yaml_content = """
name: "Mixed Enabled"
target: "node_test"
invariants:
  - name: "Enabled check"
    type: latency
    enabled: true
    config:
      max_ms: 5000
  - name: "Disabled check"
    type: latency
    enabled: false
    config:
      max_ms: 10000
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        assert inv_set.invariants[0].enabled is True
        assert inv_set.invariants[1].enabled is False


@pytest.mark.unit
class TestYamlFileLoading:
    """Test loading invariant sets from YAML files."""

    def test_load_from_file(self, tmp_path: Path) -> None:
        """Load invariant set from YAML file."""
        yaml_content = """
name: "File Test"
target: "node_file"
invariants:
  - name: "Test"
    type: latency
    config:
      max_ms: 1000
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        inv_set = load_invariant_set_from_file(str(yaml_file))
        assert inv_set.name == "File Test"

    def test_load_from_yml_extension(self, tmp_path: Path) -> None:
        """Load from file with .yml extension."""
        yaml_content = """
name: "YML Test"
target: "node_yml"
invariants:
  - name: "Test"
    type: latency
    config:
      max_ms: 1000
"""
        yml_file = tmp_path / "test.yml"
        yml_file.write_text(yaml_content)

        inv_set = load_invariant_set_from_file(str(yml_file))
        assert inv_set.name == "YML Test"

    def test_load_from_nonexistent_file_raises_error(self) -> None:
        """Loading from non-existent file raises ModelOnexError."""
        with pytest.raises((ModelOnexError, FileNotFoundError)) as exc_info:
            load_invariant_set_from_file("/nonexistent/path.yaml")

        # Check error message contains helpful info
        error_str = str(exc_info.value)
        assert (
            "not" in error_str.lower()
            or "exist" in error_str.lower()
            or "found" in error_str.lower()
        )

    def test_load_from_path_object(self, tmp_path: Path) -> None:
        """Load from Path object."""
        yaml_content = """
name: "Path Test"
target: "node_path"
invariants:
  - name: "Test"
    type: latency
    config:
      max_ms: 1000
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        inv_set = load_invariant_set_from_file(yaml_file)
        assert inv_set.name == "Path Test"


@pytest.mark.unit
class TestYamlConfigParsing:
    """Test YAML config parsing for different invariant types."""

    def test_yaml_latency_config(self) -> None:
        """Parse latency config from YAML."""
        yaml_content = """
name: "Latency Test"
target: "node_test"
invariants:
  - name: "Latency check"
    type: latency
    severity: warning
    config:
      max_ms: 5000
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        assert inv_set.invariants[0].config["max_ms"] == 5000

    def test_yaml_cost_config(self) -> None:
        """Parse cost config from YAML."""
        yaml_content = """
name: "Cost Test"
target: "node_test"
invariants:
  - name: "Cost check"
    type: cost
    severity: critical
    config:
      max_cost: 0.10
      per: request
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        assert inv_set.invariants[0].config["max_cost"] == 0.10
        assert inv_set.invariants[0].config["per"] == "request"

    def test_yaml_field_presence_config(self) -> None:
        """Parse field presence config from YAML."""
        yaml_content = """
name: "Field Presence Test"
target: "node_test"
invariants:
  - name: "Fields check"
    type: field_presence
    severity: critical
    config:
      fields:
        - response
        - model
        - usage
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        assert inv_set.invariants[0].config["fields"] == ["response", "model", "usage"]

    def test_yaml_threshold_config(self) -> None:
        """Parse threshold config from YAML."""
        yaml_content = """
name: "Threshold Test"
target: "node_test"
invariants:
  - name: "Accuracy threshold"
    type: threshold
    severity: warning
    config:
      metric_name: accuracy
      min_value: 0.95
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        assert inv_set.invariants[0].config["metric_name"] == "accuracy"
        assert inv_set.invariants[0].config["min_value"] == 0.95

    def test_yaml_schema_config(self) -> None:
        """Parse schema config from YAML."""
        yaml_content = """
name: "Schema Test"
target: "node_test"
invariants:
  - name: "Schema check"
    type: schema
    severity: critical
    config:
      json_schema:
        type: object
        required:
          - response
        properties:
          response:
            type: string
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        schema = inv_set.invariants[0].config["json_schema"]
        assert schema["type"] == "object"
        assert schema["required"] == ["response"]

    def test_yaml_field_value_config(self) -> None:
        """Parse field value config from YAML."""
        yaml_content = """
name: "Field Value Test"
target: "node_test"
invariants:
  - name: "Status check"
    type: field_value
    severity: warning
    config:
      field_path: status
      expected_value: success
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        config = inv_set.invariants[0].config
        assert config["field_path"] == "status"
        assert config["expected_value"] == "success"

    def test_yaml_custom_config(self) -> None:
        """Parse custom invariant config from YAML."""
        yaml_content = """
name: "Custom Test"
target: "node_test"
invariants:
  - name: "Custom check"
    type: custom
    severity: warning
    config:
      callable_path: my_module.my_validator
      kwargs:
        threshold: 0.9
        strict: true
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        config = inv_set.invariants[0].config
        assert config["callable_path"] == "my_module.my_validator"
        assert config["kwargs"]["threshold"] == 0.9
        assert config["kwargs"]["strict"] is True


@pytest.mark.unit
class TestYamlErrorHandling:
    """Test YAML parsing error handling."""

    def test_yaml_missing_name_field(self) -> None:
        """YAML missing required name field."""
        yaml_content = """
target: "node_test"
invariants:
  - name: "Test"
    type: latency
    config:
      max_ms: 5000
"""
        with pytest.raises((ModelOnexError, ValueError)):
            parse_invariant_set_from_yaml(yaml_content)

    def test_yaml_missing_target_field(self) -> None:
        """YAML missing required target field."""
        yaml_content = """
name: "Test"
invariants:
  - name: "Test"
    type: latency
    config:
      max_ms: 5000
"""
        with pytest.raises((ModelOnexError, ValueError)):
            parse_invariant_set_from_yaml(yaml_content)

    def test_yaml_invalid_syntax(self) -> None:
        """YAML with invalid syntax."""
        yaml_content = """
name: "Test"
target: "node_test"
invariants:
  - name: "Test"
    type: latency
    config:
      max_ms: [invalid
"""
        with pytest.raises((ModelOnexError, Exception)):
            parse_invariant_set_from_yaml(yaml_content)

    def test_yaml_empty_invariants_list(self) -> None:
        """YAML with empty invariants list is valid."""
        yaml_content = """
name: "Empty Test"
target: "node_test"
invariants: []
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)
        assert len(inv_set.invariants) == 0

    def test_yaml_invalid_severity_value(self) -> None:
        """YAML with invalid severity value."""
        yaml_content = """
name: "Test"
target: "node_test"
invariants:
  - name: "Test"
    type: latency
    severity: invalid_severity
    config:
      max_ms: 5000
"""
        with pytest.raises((ModelOnexError, ValueError)):
            parse_invariant_set_from_yaml(yaml_content)


@pytest.mark.unit
class TestYamlEdgeCases:
    """Test YAML parsing edge cases."""

    def test_yaml_with_comments(self) -> None:
        """YAML with comments should parse correctly."""
        yaml_content = """
# This is a comment
name: "Commented Set"  # inline comment
target: "node_test"
invariants:
  # Invariant comment
  - name: "Test"
    type: latency
    config:
      max_ms: 5000
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)
        assert inv_set.name == "Commented Set"

    def test_yaml_with_multiline_strings(self) -> None:
        """YAML with multiline strings."""
        yaml_content = """
name: "Multiline Test"
target: "node_test"
description: |
  This is a multiline
  description that spans
  multiple lines.
invariants:
  - name: "Test"
    type: latency
    config:
      max_ms: 5000
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)
        assert "multiline" in inv_set.description.lower()

    def test_yaml_with_anchors_and_aliases(self) -> None:
        """YAML with anchors and aliases."""
        yaml_content = """
name: "Anchor Test"
target: "node_test"
invariants:
  - name: "First"
    type: latency
    config: &latency_config
      max_ms: 5000
  - name: "Second"
    type: latency
    config: *latency_config
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)

        assert inv_set.invariants[0].config["max_ms"] == 5000
        assert inv_set.invariants[1].config["max_ms"] == 5000

    def test_yaml_with_null_values(self) -> None:
        """YAML with null values."""
        yaml_content = """
name: "Null Test"
target: "node_test"
description: null
invariants:
  - name: "Test"
    type: latency
    description: ~
    config:
      max_ms: 5000
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)
        assert inv_set.description is None
        assert inv_set.invariants[0].description is None

    def test_yaml_with_many_invariants(self) -> None:
        """YAML with many invariants."""
        invariants_yaml = "\n".join(
            [
                f"""  - name: "Check {i}"
    type: latency
    config:
      max_ms: {1000 * i}"""
                for i in range(1, 21)
            ]
        )

        yaml_content = f"""
name: "Many Invariants"
target: "node_test"
invariants:
{invariants_yaml}
"""
        inv_set = parse_invariant_set_from_yaml(yaml_content)
        assert len(inv_set.invariants) == 20


@pytest.mark.unit
class TestYamlWithFixtures:
    """Test YAML parsing with pytest fixtures."""

    def test_yaml_from_fixture(self, sample_yaml_invariant_set: str) -> None:
        """Parse YAML from conftest fixture."""
        inv_set = parse_invariant_set_from_yaml(sample_yaml_invariant_set)

        assert inv_set.name == "Test Invariant Set"
        assert inv_set.target == "node_llm_call"
        assert len(inv_set.invariants) == 2

    def test_yaml_fixture_field_presence(self, sample_yaml_invariant_set: str) -> None:
        """Field presence invariant from fixture."""
        inv_set = parse_invariant_set_from_yaml(sample_yaml_invariant_set)

        field_inv = next(
            inv
            for inv in inv_set.invariants
            if inv.type == EnumInvariantType.FIELD_PRESENCE
        )
        assert field_inv.severity == EnumSeverity.CRITICAL
        assert "response" in field_inv.config["fields"]

    def test_yaml_fixture_latency(self, sample_yaml_invariant_set: str) -> None:
        """Latency invariant from fixture."""
        inv_set = parse_invariant_set_from_yaml(sample_yaml_invariant_set)

        latency_inv = next(
            inv for inv in inv_set.invariants if inv.type == EnumInvariantType.LATENCY
        )
        assert latency_inv.severity == EnumSeverity.WARNING
        assert latency_inv.config["max_ms"] == 5000


@pytest.mark.unit
class TestDirectoryLoading:
    """Test loading invariant sets from directories."""

    def test_load_from_directory_yaml_extension(self, tmp_path: Path) -> None:
        """Load invariant sets from directory with .yaml extension."""
        yaml_content = """
name: "Test Set from YAML"
target: "node_test"
invariants:
  - name: "Latency Check"
    type: latency
    config:
      max_ms: 1000
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        sets = load_invariant_sets_from_directory(str(tmp_path))

        assert len(sets) == 1
        assert sets[0].name == "Test Set from YAML"

    def test_load_from_directory_yml_extension(self, tmp_path: Path) -> None:
        """Load invariant sets from directory with .yml extension."""
        yaml_content = """
name: "Test Set from YML"
target: "node_test"
invariants:
  - name: "Latency Check"
    type: latency
    config:
      max_ms: 2000
"""
        yml_file = tmp_path / "test.yml"
        yml_file.write_text(yaml_content)

        sets = load_invariant_sets_from_directory(str(tmp_path))

        assert len(sets) == 1
        assert sets[0].name == "Test Set from YML"

    def test_load_from_directory_both_extensions(self, tmp_path: Path) -> None:
        """Load invariant sets from directory with both .yaml and .yml files."""
        yaml_content = """
name: "Set from YAML"
target: "node_yaml"
invariants:
  - name: "Check 1"
    type: latency
    config:
      max_ms: 1000
"""
        yml_content = """
name: "Set from YML"
target: "node_yml"
invariants:
  - name: "Check 2"
    type: latency
    config:
      max_ms: 2000
"""
        yaml_file = tmp_path / "first.yaml"
        yaml_file.write_text(yaml_content)
        yml_file = tmp_path / "second.yml"
        yml_file.write_text(yml_content)

        sets = load_invariant_sets_from_directory(str(tmp_path))

        assert len(sets) == 2
        names = {s.name for s in sets}
        assert names == {"Set from YAML", "Set from YML"}

    def test_load_from_directory_nonexistent_raises_error(self) -> None:
        """Loading from nonexistent directory raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            load_invariant_sets_from_directory("/nonexistent/path")
        assert "not found" in str(exc_info.value)

    def test_load_from_directory_empty(self, tmp_path: Path) -> None:
        """Loading from empty directory returns empty list."""
        sets = load_invariant_sets_from_directory(str(tmp_path))
        assert sets == []

    def test_load_from_directory_custom_patterns(self, tmp_path: Path) -> None:
        """Load with custom patterns filters correctly."""
        yaml_content = """
name: "Custom Pattern Test"
target: "node_test"
invariants:
  - name: "Check"
    type: latency
    config:
      max_ms: 1000
"""
        # Create files with different extensions
        (tmp_path / "included.yaml").write_text(yaml_content)
        (tmp_path / "excluded.yml").write_text(yaml_content)

        # Load only .yaml files
        sets = load_invariant_sets_from_directory(str(tmp_path), patterns=["*.yaml"])

        assert len(sets) == 1
        assert sets[0].name == "Custom Pattern Test"


@pytest.mark.unit
class TestPathSecurity:
    """Test path security handling in YAML loading."""

    def test_load_file_resolves_path(self, tmp_path: Path) -> None:
        """Verify path resolution works correctly."""
        yaml_content = """
name: "Resolve Test"
target: "node_test"
invariants:
  - name: "Check"
    type: latency
    config:
      max_ms: 1000
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        # Use resolved path
        inv_set = load_invariant_set_from_file(yaml_file.resolve())
        assert inv_set.name == "Resolve Test"

    def test_load_file_not_a_file_raises_error(self, tmp_path: Path) -> None:
        """Loading a directory as a file raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            load_invariant_set_from_file(str(tmp_path))
        assert "not a file" in str(exc_info.value).lower()

    def test_load_directory_resolves_path(self, tmp_path: Path) -> None:
        """Verify directory path resolution works correctly."""
        yaml_content = """
name: "Dir Resolve Test"
target: "node_test"
invariants:
  - name: "Check"
    type: latency
    config:
      max_ms: 1000
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        # Use resolved path
        sets = load_invariant_sets_from_directory(tmp_path.resolve())
        assert len(sets) == 1
        assert sets[0].name == "Dir Resolve Test"

    def test_load_from_file_not_a_directory_raises_error(self, tmp_path: Path) -> None:
        """Loading a file as a directory raises ModelOnexError."""
        yaml_content = """
name: "Test"
target: "node_test"
invariants: []
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ModelOnexError) as exc_info:
            load_invariant_sets_from_directory(str(yaml_file))
        assert "not a directory" in str(exc_info.value).lower()

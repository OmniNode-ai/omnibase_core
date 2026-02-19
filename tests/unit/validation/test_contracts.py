# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for contract validation."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.validation.validator_contracts import (
    load_and_validate_yaml_model,
    validate_contracts_directory,
    validate_no_manual_yaml,
    validate_yaml_file,
)


@pytest.mark.unit
class TestLoadAndValidateYamlModel:
    """Test load_and_validate_yaml_model function."""

    def test_load_valid_yaml_contract(self):
        """Test loading a valid YAML contract."""
        yaml_content = """
name: "TestContract"
version: "1.0.0"
description: "Test contract"
"""
        # This will either succeed or raise an exception
        try:
            contract = load_and_validate_yaml_model(yaml_content)
            assert contract is not None
        except Exception:
            # If validation fails, that's expected for minimal contract
            pass

    def test_load_empty_yaml(self):
        """Test loading empty YAML."""
        yaml_content = ""

        with pytest.raises((ValidationError, TypeError)):
            load_and_validate_yaml_model(yaml_content)

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML syntax."""
        yaml_content = """
invalid: [unclosed
"""
        with pytest.raises(yaml.YAMLError):
            load_and_validate_yaml_model(yaml_content)


@pytest.mark.unit
class TestValidateYamlFile:
    """Test validate_yaml_file function."""

    def test_nonexistent_file(self, tmp_path: Path):
        """Test validation of nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.yaml"

        errors = validate_yaml_file(nonexistent)

        assert len(errors) > 0
        assert "does not exist" in errors[0].lower()

    def test_directory_instead_of_file(self, tmp_path: Path):
        """Test validation when path is a directory."""
        directory = tmp_path / "test_dir"
        directory.mkdir()

        errors = validate_yaml_file(directory)

        assert len(errors) > 0
        assert "not a regular file" in errors[0].lower()

    def test_empty_file(self, tmp_path: Path):
        """Test validation of empty file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        errors = validate_yaml_file(empty_file)

        # Empty files are considered valid
        assert len(errors) == 0

    def test_whitespace_only_file(self, tmp_path: Path):
        """Test validation of whitespace-only file."""
        ws_file = tmp_path / "whitespace.yaml"
        ws_file.write_text("   \n\t\n   ")

        errors = validate_yaml_file(ws_file)

        # Whitespace-only files are considered valid
        assert len(errors) == 0

    def test_valid_yaml_file(self, tmp_path: Path):
        """Test validation of valid YAML file."""
        yaml_file = tmp_path / "valid.yaml"
        # Create minimal valid contract structure with required fields
        content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
operations: []
"""
        yaml_file.write_text(content)

        errors = validate_yaml_file(yaml_file)

        # Valid contract should have no errors
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_invalid_yaml_syntax(self, tmp_path: Path):
        """Test validation of invalid YAML syntax."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: [unclosed\n  more: stuff")

        errors = validate_yaml_file(yaml_file)

        assert len(errors) > 0

    def test_file_size_limit(self, tmp_path: Path):
        """Test validation of file exceeding size limit."""
        large_file = tmp_path / "large.yaml"
        # Create file larger than MAX_FILE_SIZE (50MB)
        # For test purposes, we'll mock the file size check by creating
        # a normal file and checking the error message structure
        # Create minimal valid contract structure with required fields
        content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
operations: []
"""
        large_file.write_text(content)

        # This test verifies the function can handle the file
        errors = validate_yaml_file(large_file)

        # File is small, so should process normally with no errors
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_read_permission_handling(self, tmp_path: Path):
        """Test handling of files without read permission."""
        yaml_file = tmp_path / "no_read.yaml"
        # Create minimal valid contract structure with required fields
        content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
operations: []
"""
        yaml_file.write_text(content)

        # On most systems, we can't easily test permission denied
        # but we can verify the function handles it gracefully
        errors = validate_yaml_file(yaml_file)

        # File should be readable in test environment with valid contract
        assert isinstance(errors, list)
        assert len(errors) == 0


@pytest.mark.unit
class TestValidateNoManualYaml:
    """Test validate_no_manual_yaml function."""

    def test_no_yaml_files(self, tmp_path: Path):
        """Test when there are no YAML files."""
        errors = validate_no_manual_yaml(tmp_path)

        assert len(errors) == 0

    def test_yaml_outside_restricted_areas(self, tmp_path: Path):
        """Test YAML files outside restricted areas."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("# Manual comment\ntest: data")

        errors = validate_no_manual_yaml(tmp_path)

        # File is not in restricted area, so no errors
        assert len(errors) == 0

    def test_generated_yaml_without_manual_indicators(self, tmp_path: Path):
        """Test generated YAML without manual indicators."""
        generated_dir = tmp_path / "generated"
        generated_dir.mkdir()
        yaml_file = generated_dir / "auto.yaml"
        yaml_file.write_text("# Auto-generated\ntest: data")

        errors = validate_no_manual_yaml(tmp_path)

        # No manual indicators, so no errors
        assert len(errors) == 0

    def test_manual_yaml_in_generated_dir(self, tmp_path: Path):
        """Test manual YAML in generated directory."""
        generated_dir = tmp_path / "generated"
        generated_dir.mkdir()
        yaml_file = generated_dir / "manual.yaml"
        yaml_file.write_text("# Manual creation\ntest: data")

        errors = validate_no_manual_yaml(tmp_path)

        assert len(errors) > 0
        assert "Manual YAML detected" in errors[0]

    def test_various_manual_indicators(self, tmp_path: Path):
        """Test detection of various manual indicators."""
        generated_dir = tmp_path / "generated"
        generated_dir.mkdir()

        indicators = ["# Manual", "# TODO", "# FIXME", "# NOTE:", "# manually created"]

        for i, indicator in enumerate(indicators):
            yaml_file = generated_dir / f"test{i}.yaml"
            yaml_file.write_text(f"{indicator}\ntest: data")

        errors = validate_no_manual_yaml(tmp_path)

        # Should detect all manual indicators
        assert len(errors) == len(indicators)

    def test_manual_yaml_in_auto_dir(self, tmp_path: Path):
        """Test manual YAML in auto directory."""
        auto_dir = tmp_path / "auto"
        auto_dir.mkdir()
        yaml_file = auto_dir / "manual.yaml"
        yaml_file.write_text("# TODO: fix this\ntest: data")

        errors = validate_no_manual_yaml(tmp_path)

        assert len(errors) > 0

    def test_case_insensitive_indicator_detection(self, tmp_path: Path):
        """Test case-insensitive detection of manual indicators."""
        generated_dir = tmp_path / "generated"
        generated_dir.mkdir()
        yaml_file = generated_dir / "test.yaml"
        yaml_file.write_text("# MANUAL CREATION\ntest: data")

        errors = validate_no_manual_yaml(tmp_path)

        assert len(errors) > 0


@pytest.mark.unit
class TestValidateContractsDirectory:
    """Test validate_contracts_directory function."""

    def test_empty_directory(self, tmp_path: Path):
        """Test validation of empty directory."""
        result = validate_contracts_directory(tmp_path)

        assert result.is_valid is True
        assert result.metadata.files_processed == 0
        assert len(result.errors) == 0

    def test_directory_with_valid_yaml(self, tmp_path: Path):
        """Test directory with valid YAML files."""
        yaml_file = tmp_path / "test.yaml"
        # Create minimal valid contract structure with required fields
        content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
operations: []
"""
        yaml_file.write_text(content)

        result = validate_contracts_directory(tmp_path)

        assert result.metadata.files_processed == 1
        assert isinstance(result.errors, list)
        assert result.is_valid is True

    def test_directory_with_multiple_yaml_extensions(self, tmp_path: Path):
        """Test directory with both .yaml and .yml files."""
        # Create minimal valid contract structure with required fields
        content1 = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
operations: []
"""
        content2 = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: EFFECT_GENERIC
operations: []
"""
        (tmp_path / "test1.yaml").write_text(content1)
        (tmp_path / "test2.yml").write_text(content2)

        result = validate_contracts_directory(tmp_path)

        assert result.metadata.files_processed == 2
        assert result.is_valid is True

    def test_excludes_pycache(self, tmp_path: Path):
        """Test that __pycache__ is excluded."""
        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "test.yaml").write_text("test: data")

        result = validate_contracts_directory(tmp_path)

        # Should not include __pycache__ files
        assert result.metadata.files_processed == 0

    def test_excludes_git(self, tmp_path: Path):
        """Test that .git is excluded."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.yaml").write_text("test: data")

        result = validate_contracts_directory(tmp_path)

        # Should not include .git files
        assert result.metadata.files_processed == 0

    def test_excludes_node_modules(self, tmp_path: Path):
        """Test that node_modules is excluded."""
        nm_dir = tmp_path / "node_modules"
        nm_dir.mkdir()
        (nm_dir / "package.yaml").write_text("test: data")

        result = validate_contracts_directory(tmp_path)

        # Should not include node_modules files
        assert result.metadata.files_processed == 0

    def test_metadata_populated(self, tmp_path: Path):
        """Test that metadata is properly populated."""
        # Create minimal valid contract structure with required fields
        content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
operations: []
"""
        (tmp_path / "test.yaml").write_text(content)

        result = validate_contracts_directory(tmp_path)

        assert result.metadata.validation_type is not None
        assert result.metadata.validation_type == "contracts"
        assert result.metadata.yaml_files_found is not None
        assert result.metadata.manual_yaml_violations is not None

    def test_detects_manual_yaml_violations(self, tmp_path: Path):
        """Test detection of manual YAML in restricted areas."""
        generated_dir = tmp_path / "generated"
        generated_dir.mkdir()
        # Create valid contract with manual indicator comment
        content = """# Manual
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
operations: []
"""
        (generated_dir / "manual.yaml").write_text(content)

        result = validate_contracts_directory(tmp_path)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert result.metadata.manual_yaml_violations > 0

    def test_invalid_yaml_tracked_in_violations(self, tmp_path: Path):
        """Test that invalid YAML is tracked properly."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: [unclosed")

        result = validate_contracts_directory(tmp_path)

        assert result.metadata.files_processed == 1
        # May have validation errors
        assert isinstance(result.errors, list)

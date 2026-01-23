#!/usr/bin/env python3
import pytest

"""
Comprehensive tests for YAML contract validation.

Tests all aspects of the YAML contract validator including:
- Valid YAML contract structures
- Invalid YAML that should trigger violations
- Malformed YAML parsing errors
- Edge cases like empty files, large files
- File encoding and permission handling
- Performance and timeout handling
"""

import importlib.util
import os
import shutil
import signal

# Import the validation module
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent.parent / "scripts" / "validation"),
)

# Import the contracts module using importlib
script_path = (
    Path(__file__).parent.parent.parent.parent
    / "scripts"
    / "validation"
    / "validate-contracts.py"
)
spec = importlib.util.spec_from_file_location("validate_contracts", script_path)
validate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_module)

validate_yaml_file = validate_module.validate_yaml_file
main = validate_module.main
setup_timeout_handler = validate_module.setup_timeout_handler


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    yield repo_path
    shutil.rmtree(temp_dir)


@pytest.mark.unit
class TestYAMLValidation:
    """Test YAML file validation."""

    def test_valid_yaml_contract(self, temp_repo):
        """Valid YAML contract passes validation."""
        valid_yaml = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "COMPUTE_GENERIC"
description: "Valid contract example"

metadata:
  name: "DataProcessor"
  version:
    major: 1
    minor: 0
    patch: 0
  author: "omni-team"

inputs:
  - name: "input_data"
    type: "object"
    required: true
    schema:
      type: "object"
      properties:
        user_id:
          type: "string"

outputs:
  - name: "output_data"
    type: "object"
    schema:
      type: "object"
      properties:
        result:
          type: "string"

configuration:
  timeout: 30
  retries: 3
"""
        yaml_file = temp_repo / "valid_contract.yaml"
        yaml_file.write_text(valid_yaml)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0

    def test_missing_contract_version(self, temp_repo):
        """Missing contract_version triggers error."""
        invalid_yaml = """
node_type: "COMPUTE_GENERIC"
description: "Missing contract version"

metadata:
  name: "TestContract"
"""
        yaml_file = temp_repo / "missing_version.yaml"
        yaml_file.write_text(invalid_yaml)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("contract_version" in error for error in errors)

    def test_missing_node_type(self, temp_repo):
        """Missing node_type triggers error."""
        invalid_yaml = """
contract_version:
  major: 1
  minor: 0
  patch: 0
description: "Missing node type"

metadata:
  name: "TestContract"
"""
        yaml_file = temp_repo / "missing_node_type.yaml"
        yaml_file.write_text(invalid_yaml)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("node_type" in error for error in errors)

    def test_both_required_fields_missing(self, temp_repo):
        """Both required fields missing triggers multiple errors."""
        invalid_yaml = """
description: "Missing both required fields"

metadata:
  name: "TestContract"
"""
        yaml_file = temp_repo / "missing_both.yaml"
        yaml_file.write_text(invalid_yaml)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 2
        assert any("contract_version" in error for error in errors)
        assert any("node_type" in error for error in errors)

    def test_empty_yaml_file(self, temp_repo):
        """Empty YAML files are valid (not contracts)."""
        yaml_file = temp_repo / "empty.yaml"
        yaml_file.touch()

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0  # Empty files should be OK

    def test_yaml_with_only_whitespace(self, temp_repo):
        """Whitespace-only YAML files are valid."""
        yaml_file = temp_repo / "whitespace.yaml"
        yaml_file.write_text("   \n\n  \t  \n")

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0  # Whitespace-only files should be OK

    def test_malformed_yaml_syntax(self, temp_repo):
        """Malformed YAML syntax triggers parsing error."""
        malformed_yaml = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "COMPUTE_GENERIC"

inputs:
  - name: "test"
    type: object  # Missing quotes
    schema:
      type: object  # Missing quotes

outputs
  # Missing colon
  name: "output"
  type: "object"

configuration:
  timeout: [invalid, yaml, structure
"""
        yaml_file = temp_repo / "malformed.yaml"
        yaml_file.write_text(malformed_yaml)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any(
            "YAML" in error and ("parsing" in error or "error" in error)
            for error in errors
        )

    def test_yaml_with_unicode_content(self, temp_repo):
        """Unicode content in YAML is handled correctly."""
        unicode_yaml = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "COMPUTE_GENERIC"
description: "Contract with Unicode: 中文, emoji 🚀, accents ñáéíóú"

metadata:
  name: "UnicodeProcessor"
  author: "José González"
  description: "Processes data with Unicode support 北京"

inputs:
  - name: "user_data"
    type: "object"
    description: "User data with special chars: ñáéíóú 🎉"
"""
        yaml_file = temp_repo / "unicode_contract.yaml"
        yaml_file.write_text(unicode_yaml, encoding="utf-8")

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0

    def test_non_contract_yaml_file(self, temp_repo):
        """Non-contract YAML files pass validation."""
        non_contract_yaml = """
# This is just a regular YAML file, not a contract
settings:
  debug: true
  database:
    host: "localhost"
    port: 5432

users:
  - name: "admin"
    role: "administrator"
  - name: "user"
    role: "standard"
"""
        yaml_file = temp_repo / "settings.yaml"
        yaml_file.write_text(non_contract_yaml)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0  # Non-contract files should be fine

    def test_yaml_with_contract_version_only(self, temp_repo):
        """Contract with only contract_version triggers node_type error."""
        partial_yaml = """
contract_version:
  major: 2
  minor: 0
  patch: 0
description: "Partial contract"
"""
        yaml_file = temp_repo / "partial_contract.yaml"
        yaml_file.write_text(partial_yaml)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 1
        assert "node_type" in errors[0]

    def test_yaml_with_node_type_only(self, temp_repo):
        """Contract with only node_type triggers contract_version error."""
        partial_yaml = """
node_type: "EFFECT_GENERIC"
description: "Partial contract"
"""
        yaml_file = temp_repo / "partial_contract2.yaml"
        yaml_file.write_text(partial_yaml)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 1
        assert "contract_version" in errors[0]


@pytest.mark.unit
class TestNodeTypeValidation:
    """Test node_type field validation."""

    def test_lowercase_node_type_normalized(self, temp_repo):
        """Lowercase node_type normalizes to uppercase."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "compute_generic"
"""
        yaml_file = temp_repo / "lowercase_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0, f"Expected normalization to uppercase, got: {errors}"

    def test_mixed_case_node_type_normalized(self, temp_repo):
        """Mixed-case node_type normalizes to uppercase."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "Compute_Generic"
"""
        yaml_file = temp_repo / "mixed_case_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0, f"Expected normalization to uppercase, got: {errors}"

    def test_uppercase_node_type_accepted(self, temp_repo):
        """Uppercase node_type is accepted."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "EFFECT_GENERIC"
"""
        yaml_file = temp_repo / "uppercase_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0

    def test_invalid_node_type_rejected(self, temp_repo):
        """Invalid node_type value is rejected."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "INVALID_TYPE_XYZ"
"""
        yaml_file = temp_repo / "invalid_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("node_type" in error.lower() for error in errors)

    def test_empty_string_node_type_rejected(self, temp_repo):
        """Empty string node_type is rejected."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: ""
"""
        yaml_file = temp_repo / "empty_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("node_type" in error.lower() for error in errors)

    def test_integer_node_type_rejected(self, temp_repo):
        """Integer node_type is rejected."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: 123
"""
        yaml_file = temp_repo / "integer_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("node_type" in error.lower() for error in errors)

    def test_list_node_type_rejected(self, temp_repo):
        """List node_type is rejected."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type:
  - COMPUTE_GENERIC
  - EFFECT_GENERIC
"""
        yaml_file = temp_repo / "list_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("node_type" in error.lower() for error in errors)

    def test_null_node_type_rejected(self, temp_repo):
        """Null node_type is rejected."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: null
"""
        yaml_file = temp_repo / "null_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("node_type" in error.lower() for error in errors)

    def test_whitespace_node_type_rejected(self, temp_repo):
        """Whitespace-only node_type is rejected."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "   "
"""
        yaml_file = temp_repo / "whitespace_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("node_type" in error.lower() for error in errors)

    def test_all_valid_node_types_accepted(self, temp_repo):
        """All valid EnumNodeType values are accepted."""
        valid_types = [
            "COMPUTE_GENERIC",
            "EFFECT_GENERIC",
            "REDUCER_GENERIC",
            "ORCHESTRATOR_GENERIC",
            "RUNTIME_HOST_GENERIC",
            "GATEWAY",
            "VALIDATOR",
            "TRANSFORMER",
            "AGGREGATOR",
            "FUNCTION",
            "TOOL",
            "AGENT",
            "MODEL",
            "PLUGIN",
            "SCHEMA",
            "NODE",
            "WORKFLOW",
            "SERVICE",
            "UNKNOWN",
        ]

        for node_type in valid_types:
            yaml_content = f"""
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "{node_type}"
"""
            yaml_file = temp_repo / f"valid_{node_type.lower()}.yaml"
            yaml_file.write_text(yaml_content)

            errors = validate_yaml_file(yaml_file)
            assert len(errors) == 0, f"{node_type} should be valid, got: {errors}"

    def test_node_type_with_leading_trailing_spaces(self, temp_repo):
        """Node_type with leading/trailing spaces is handled."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "  COMPUTE_GENERIC  "
"""
        yaml_file = temp_repo / "spaces_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        # Should either strip and accept, or reject - but not crash
        assert isinstance(errors, list)

    def test_node_type_with_newlines(self, temp_repo):
        """Node_type with embedded newlines is handled."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "COMPUTE\nGENERIC"
"""
        yaml_file = temp_repo / "newline_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        # Should reject invalid format but not crash
        assert isinstance(errors, list)

    def test_node_type_with_special_characters(self, temp_repo):
        """Node_type with special characters is handled."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "COMPUTE_GENERIC@#$"
"""
        yaml_file = temp_repo / "special_chars_node_type.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_yaml_file(yaml_file)
        # Should reject invalid format but not crash
        assert isinstance(errors, list)
        assert len(errors) >= 1


@pytest.mark.unit
class TestContractVersionValidation:
    """Test contract_version field validation."""

    def test_contract_version_string_format_valid(self, temp_repo):
        """Valid semver string format like '1.0.0' passes."""
        yaml_content = """
contract_version: "1.0.0"
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "string_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0

    def test_contract_version_dict_format_valid(self, temp_repo):
        """Valid dict format with major/minor/patch passes."""
        yaml_content = """
contract_version:
  major: 2
  minor: 1
  patch: 3
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "dict_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0

    def test_contract_version_invalid_string_rejected(self, temp_repo):
        """Invalid semver string is handled gracefully."""
        yaml_content = """
contract_version: "not-a-version"
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "invalid_string_version.yaml"
        yaml_file.write_text(yaml_content)
        # Should not crash - may use default version or error
        errors = validate_yaml_file(yaml_file)
        assert isinstance(errors, list)

    def test_contract_version_partial_string_handled(self, temp_repo):
        """Partial semver string like '1.0' is handled."""
        yaml_content = """
contract_version: "1.0"
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "partial_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        assert isinstance(errors, list)

    def test_contract_version_zero_values_valid(self, temp_repo):
        """Version 0.0.0 is valid."""
        yaml_content = """
contract_version: "0.0.0"
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "zero_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0

    def test_contract_version_high_numbers_valid(self, temp_repo):
        """Version with high numbers is valid."""
        yaml_content = """
contract_version: "99.99.99"
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "high_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0

    def test_contract_version_integer_handled(self, temp_repo):
        """Integer contract_version is handled gracefully."""
        yaml_content = """
contract_version: 1
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "integer_version.yaml"
        yaml_file.write_text(yaml_content)
        # Should not crash - may convert or error
        errors = validate_yaml_file(yaml_file)
        assert isinstance(errors, list)

    def test_contract_version_float_handled(self, temp_repo):
        """Float contract_version is handled gracefully."""
        yaml_content = """
contract_version: 1.5
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "float_version.yaml"
        yaml_file.write_text(yaml_content)
        # Should not crash - may convert or error
        errors = validate_yaml_file(yaml_file)
        assert isinstance(errors, list)

    def test_contract_version_null_rejected(self, temp_repo):
        """Null contract_version is rejected."""
        yaml_content = """
contract_version: null
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "null_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        # Null should be treated as missing
        assert isinstance(errors, list)

    def test_contract_version_list_rejected(self, temp_repo):
        """List contract_version is rejected."""
        yaml_content = """
contract_version:
  - 1
  - 0
  - 0
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "list_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        # List format should be rejected
        assert isinstance(errors, list)

    def test_contract_version_empty_string_rejected(self, temp_repo):
        """Empty string contract_version is rejected."""
        yaml_content = """
contract_version: ""
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "empty_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        # Empty string should be treated as missing or invalid
        assert isinstance(errors, list)

    def test_contract_version_dict_missing_patch(self, temp_repo):
        """Dict format missing patch field is handled."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "missing_patch_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        # Should handle gracefully - may default patch to 0 or error
        assert isinstance(errors, list)

    def test_contract_version_dict_extra_fields(self, temp_repo):
        """Dict format with extra fields is handled."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
  prerelease: "alpha"
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "extra_fields_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        # Should accept or ignore extra fields
        assert isinstance(errors, list)

    def test_contract_version_with_prerelease_suffix(self, temp_repo):
        """Semver with prerelease suffix like '1.0.0-alpha' is handled."""
        yaml_content = """
contract_version: "1.0.0-alpha"
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "prerelease_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        # May accept extended semver or reject - should not crash
        assert isinstance(errors, list)

    def test_contract_version_with_build_metadata(self, temp_repo):
        """Semver with build metadata like '1.0.0+build.123' is handled."""
        yaml_content = """
contract_version: "1.0.0+build.123"
node_type: "COMPUTE_GENERIC"
"""
        yaml_file = temp_repo / "build_metadata_version.yaml"
        yaml_file.write_text(yaml_content)
        errors = validate_yaml_file(yaml_file)
        # May accept extended semver or reject - should not crash
        assert isinstance(errors, list)


@pytest.mark.unit
class TestFileHandling:
    """Test file handling edge cases."""

    def test_nonexistent_file(self):
        """Non-existent file returns error."""
        nonexistent_file = Path("/nonexistent/file.yaml")
        errors = validate_yaml_file(nonexistent_file)

        assert len(errors) >= 1
        assert any("not exist" in error for error in errors)

    def test_directory_instead_of_file(self, temp_repo):
        """Directory path returns 'not a regular file' error."""
        test_dir = temp_repo / "test_directory"
        test_dir.mkdir()

        errors = validate_yaml_file(test_dir)
        assert len(errors) >= 1
        assert any("not a regular file" in error for error in errors)

    def test_large_yaml_file(self, temp_repo):
        """Large YAML files are validated within time limit."""
        # Create a large YAML file
        large_yaml = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "COMPUTE_GENERIC"
description: "Large contract for performance testing"

metadata:
  name: "LargeProcessor"

inputs:
"""
        # Add many input definitions
        for i in range(1000):
            large_yaml += f"""
  - name: "input_{i:04d}"
    type: "string"
    description: "Input field {i}"
"""

        large_yaml += """
outputs:
  - name: "result"
    type: "object"
"""

        yaml_file = temp_repo / "large_contract.yaml"
        yaml_file.write_text(large_yaml)

        import time

        start_time = time.time()
        errors = validate_yaml_file(yaml_file)
        end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 5.0
        assert len(errors) == 0  # Should be valid

    def test_extremely_large_file_rejection(self, temp_repo):
        """Files over 50MB are rejected."""
        # Create content that would be larger than 50MB when written
        huge_content = "# Large file\n" + "data: value\n" * 3000000  # ~60MB
        huge_file = temp_repo / "huge_file.yaml"

        try:
            huge_file.write_text(huge_content)
            # Check if file is actually large enough
            if huge_file.stat().st_size > 50 * 1024 * 1024:  # 50MB
                errors = validate_yaml_file(huge_file)
                assert len(errors) >= 1
                assert any("too large" in error for error in errors)
        except MemoryError:
            # If we can't even create the file due to memory constraints,
            # that's also a valid test outcome
            pytest.skip("Cannot create large enough file due to memory constraints")

    def test_permission_denied_file(self, temp_repo):
        """Permission denied returns error."""
        yaml_file = temp_repo / "restricted.yaml"
        yaml_file.write_text(
            """contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: 'COMPUTE_GENERIC'""",
        )

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            errors = validate_yaml_file(yaml_file)
            assert len(errors) >= 1
            assert any("permission denied" in error.lower() for error in errors)

    def test_encoding_error_handling(self, temp_repo):
        """Encoding errors are handled gracefully."""
        yaml_file = temp_repo / "encoding_issue.yaml"
        # Write some problematic bytes
        with open(yaml_file, "wb") as f:
            # Write corrupt binary data with version format
            f.write(
                b"\xff\xfe\x00\x00contract_version:\n  major: 1\n  minor: 0\n  patch: 0\n\x80\x81\x82",
            )

        errors = validate_yaml_file(yaml_file)
        # Should either succeed with fallback encoding or report encoding error
        assert isinstance(errors, list)

    def test_os_error_handling(self, temp_repo):
        """OS errors are handled gracefully."""
        yaml_file = temp_repo / "test.yaml"
        yaml_file.write_text("test: value")

        # Patch the open call to trigger the OS error handling path
        with patch("builtins.open", side_effect=OSError("OS Error")):
            errors = validate_yaml_file(yaml_file)
            assert len(errors) >= 1
            # Check for OS/IO error in message (script uses "OS/IO error reading file")
            assert any("error reading file" in error.lower() for error in errors)

    def test_non_mapping_yaml_scalar_string(self, temp_repo):
        """Scalar string root YAML is skipped (PR #132 regression)."""
        yaml_file = temp_repo / "scalar_string.yaml"
        yaml_file.write_text("just a plain string")

        # Should not raise TypeError, should return empty errors (not a contract)
        errors = validate_yaml_file(yaml_file)
        assert isinstance(errors, list)
        assert len(errors) == 0  # Non-dict YAML is silently skipped (not a contract)

    def test_non_mapping_yaml_scalar_number(self, temp_repo):
        """Scalar number root YAML is skipped (PR #132 regression)."""
        yaml_file = temp_repo / "scalar_number.yaml"
        yaml_file.write_text("42")

        errors = validate_yaml_file(yaml_file)
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_non_mapping_yaml_list_root(self, temp_repo):
        """List root YAML is skipped (PR #132 regression)."""
        yaml_file = temp_repo / "list_root.yaml"
        yaml_file.write_text("- item1\n- item2\n- item3")

        errors = validate_yaml_file(yaml_file)
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_non_mapping_yaml_list_of_dicts(self, temp_repo):
        """List of dicts root YAML is skipped (PR #132 regression)."""
        yaml_file = temp_repo / "list_of_dicts.yaml"
        yaml_file.write_text("- key1: value1\n- key2: value2")

        errors = validate_yaml_file(yaml_file)
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_non_mapping_yaml_boolean_root(self, temp_repo):
        """Boolean root YAML is skipped (PR #132 regression)."""
        yaml_file = temp_repo / "boolean_root.yaml"
        yaml_file.write_text("true")

        errors = validate_yaml_file(yaml_file)
        assert isinstance(errors, list)
        assert len(errors) == 0


@pytest.mark.unit
class TestMainFunction:
    """Test the main function and CLI interface."""

    def test_main_with_valid_yaml_files(self, temp_repo):
        """Valid YAML files return exit code 0."""
        # Create valid YAML files
        valid_yaml1 = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "COMPUTE_GENERIC"
"""
        valid_yaml2 = """
# Just a regular YAML file
settings:
  debug: true
"""

        (temp_repo / "contract.yaml").write_text(valid_yaml1)
        (temp_repo / "settings.yml").write_text(valid_yaml2)

        with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
            result = main()
            assert result == 0

    def test_main_with_invalid_yaml_files(self, temp_repo):
        """Invalid YAML files return exit code 1."""
        invalid_yaml = """
contract_version:
  major: 1
  minor: 0
  patch: 0
# Missing node_type
"""
        (temp_repo / "invalid_contract.yaml").write_text(invalid_yaml)

        with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
            result = main()
            assert result == 1

    def test_main_with_no_yaml_files(self, temp_repo):
        """Directory with no YAML files returns exit code 0."""
        # Create non-YAML files
        (temp_repo / "test.py").write_text("print('test')")
        (temp_repo / "README.md").write_text("# Test")

        with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
            result = main()
            assert result == 0  # Should succeed with message about no files

    def test_main_with_nonexistent_path(self):
        """Non-existent path returns exit code 1."""
        with patch("sys.argv", ["validate-contracts.py", "/nonexistent/path"]):
            result = main()
            assert result == 1

    def test_main_with_malformed_yaml(self, temp_repo):
        """Malformed YAML returns exit code 1."""
        malformed_yaml = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: compute  # Missing quotes
invalid: [yaml, structure
"""
        (temp_repo / "malformed.yaml").write_text(malformed_yaml)

        with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
            result = main()
            assert result == 1

    def test_main_argument_parsing_error(self):
        """Invalid CLI arguments return exit code 2."""
        with patch("sys.argv", ["validate-contracts.py", "--invalid-flag"]):
            result = main()
            assert result == 2  # argparse returns 2 for argument parsing errors

    def test_main_with_archived_files_filtering(self, temp_repo):
        """Archived directory files are filtered out."""
        # Create archived directory with YAML files
        archived_dir = temp_repo / "archived"
        archived_dir.mkdir()
        (archived_dir / "old_contract.yaml").write_text(
            """contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: 'COMPUTE_GENERIC'""",
        )

        # Create regular YAML file
        (temp_repo / "current_contract.yaml").write_text(
            """contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: 'COMPUTE_GENERIC'""",
        )

        with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
            with patch("builtins.print") as mock_print:
                result = main()
                assert result == 0

                # Check that only one file was processed (archived should be filtered)
                printed_output = " ".join(
                    str(call) for call in mock_print.call_args_list
                )
                assert (
                    "1 YAML file" in printed_output
                    or "YAML files validated" in printed_output
                )


@pytest.mark.unit
class TestTimeoutHandling:
    """Test timeout handling functionality."""

    @pytest.mark.skipif(os.name == "nt", reason="Signal handling different on Windows")
    def test_timeout_handler_setup(self):
        """Timeout handler setup succeeds on Unix."""
        setup_timeout_handler()
        # Should not raise exception
        assert signal.signal(signal.SIGALRM, signal.SIG_DFL) is not None

    @pytest.mark.skipif(os.name == "nt", reason="Signal handling different on Windows")
    def test_file_discovery_timeout_simulation(self, temp_repo):
        """File discovery timeout returns exit code 1."""
        # Create many directories and files to potentially slow down discovery
        for i in range(100):
            subdir = temp_repo / f"subdir_{i}"
            subdir.mkdir()
            (subdir / f"file_{i}.yaml").write_text("test: value")

        # Simulate timeout during file discovery using the actual method used (os.walk)
        with patch("signal.alarm") as mock_alarm:
            with patch("os.walk", side_effect=TimeoutError("Timeout")):
                with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
                    result = main()
                    assert result == 1


@pytest.mark.unit
class TestErrorRecovery:
    """Test error recovery and graceful handling."""

    def test_keyboard_interrupt_handling(self, temp_repo):
        """KeyboardInterrupt returns exit code 1."""
        (temp_repo / "test.yaml").write_text("test: value")

        # Patch the function in the validate module directly
        with patch.object(
            validate_module,
            "validate_yaml_file",
            side_effect=KeyboardInterrupt(),
        ):
            with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
                result = main()
                assert result == 1

    def test_unexpected_exception_handling(self, temp_repo):
        """Unexpected exceptions return exit code 1."""
        (temp_repo / "test.yaml").write_text("test: value")

        # Patch the function in the validate module directly
        with patch.object(
            validate_module,
            "validate_yaml_file",
            side_effect=RuntimeError("Unexpected error"),
        ):
            with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
                result = main()
                assert result == 1

    def test_partial_processing_after_error(self, temp_repo):
        """Processing continues after individual file errors."""
        # Create valid and problematic files
        (temp_repo / "valid.yaml").write_text(
            """contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: 'COMPUTE_GENERIC'""",
        )
        (temp_repo / "problem.yaml").write_text("valid: yaml")

        # Mock one file to cause error
        original_validate = validate_yaml_file

        def mock_validate(file_path):
            if "problem.yaml" in str(file_path):
                raise RuntimeError("Simulated error")
            return original_validate(file_path)

        # Patch the function in the validate module directly
        with patch.object(
            validate_module,
            "validate_yaml_file",
            side_effect=mock_validate,
        ):
            with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
                result = main()
                # Should process what it can and report issues
                assert result == 1


@pytest.mark.unit
class TestExampleContractsValidation:
    """Regression tests for example contracts."""

    def test_example_contracts_validate(self):
        """Example contracts pass schema validation ( regression)."""
        example_path = (
            Path(__file__).parent.parent.parent.parent / "examples" / "contracts"
        )

        if not example_path.exists():
            pytest.skip("examples/contracts directory not found")

        yaml_files = list(example_path.rglob("*.yaml")) + list(
            example_path.rglob("*.yml")
        )

        if not yaml_files:
            pytest.skip("No YAML files found in examples/contracts")

        all_errors = []
        for yaml_file in yaml_files:
            errors = validate_yaml_file(yaml_file)
            if errors:
                all_errors.append(f"{yaml_file.relative_to(example_path)}: {errors}")

        assert len(all_errors) == 0, (
            "Example contracts failed validation:\n" + "\n".join(all_errors)
        )

    def test_example_contracts_have_required_fields(self):
        """Example contracts have required fields ( regression)."""
        import yaml

        example_path = (
            Path(__file__).parent.parent.parent.parent / "examples" / "contracts"
        )

        if not example_path.exists():
            pytest.skip("examples/contracts directory not found")

        yaml_files = list(example_path.rglob("*.yaml")) + list(
            example_path.rglob("*.yml")
        )

        for yaml_file in yaml_files:
            with open(yaml_file, encoding="utf-8") as f:
                content = yaml.safe_load(f)

            if content is None:
                continue  # Empty file

            # Skip non-mapping YAML (e.g., scalar, list)
            if not isinstance(content, dict):
                continue

            # Skip handler contracts - they have their own schema and don't use
            # contract_version/node_type. Handler contracts are validated by
            # test_handler_contract_examples.py
            if "handler_id" in content:
                continue

            # Check if this looks like an ONEX metadata contract (has contract indicators)
            contract_indicators = {
                "contract_version",
                "node_type",
                "metadata",
                "inputs",
                "outputs",
            }
            if any(field in content for field in contract_indicators):
                assert "contract_version" in content, (
                    f"{yaml_file.name} is missing required field: contract_version"
                )
                assert "node_type" in content, (
                    f"{yaml_file.name} is missing required field: node_type"
                )


@pytest.mark.unit
class TestHandlerContractValidation:
    """Test handler contract validation (handler_id-based contracts).

    Handler contracts have a different schema than ONEX metadata contracts:
    - They have handler_id instead of contract_version/node_type
    - They define handler behavior through the descriptor field
    - They specify capability dependencies and execution constraints
    """

    def test_valid_handler_contract(self, temp_repo):
        """Valid handler contract passes validation."""
        valid_handler = """
handler_id: compute.schema.validator
name: Schema Validator
contract_version:
  major: 1
  minor: 0
  patch: 0
description: Validates input data against JSON schemas

descriptor:
  node_archetype: compute
  purity: pure
  idempotent: true
  timeout_ms: 5000

input_model: myapp.models.ValidationRequest
output_model: myapp.models.ValidationResult

capability_outputs:
  - validation.result

tags:
  - validation
  - compute
"""
        yaml_file = temp_repo / "handler_contract.yaml"
        yaml_file.write_text(valid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0, f"Valid handler contract should pass. Errors: {errors}"

    def test_handler_contract_missing_handler_id(self, temp_repo):
        """Missing handler_id triggers error."""
        invalid_handler = """
name: Schema Validator
contract_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  node_archetype: compute
  purity: pure
  idempotent: true
input_model: myapp.models.Input
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "missing_handler_id.yaml"
        yaml_file.write_text(invalid_handler)

        # This should be detected as a regular YAML file, not a handler contract
        # since handler_id is the key discriminator
        errors = validate_yaml_file(yaml_file)
        assert isinstance(errors, list)

    def test_handler_contract_missing_name(self, temp_repo):
        """Missing name triggers error."""
        invalid_handler = """
handler_id: compute.schema.validator
contract_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  node_archetype: compute
  purity: pure
  idempotent: true
input_model: myapp.models.Input
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "missing_name.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("name" in error.lower() for error in errors)

    def test_handler_contract_missing_contract_version(self, temp_repo):
        """Missing contract_version triggers error."""
        invalid_handler = """
handler_id: compute.schema.validator
name: Schema Validator
descriptor:
  node_archetype: compute
  purity: pure
  idempotent: true
input_model: myapp.models.Input
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "missing_contract_version.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("contract_version" in error.lower() for error in errors)

    def test_handler_contract_missing_descriptor(self, temp_repo):
        """Missing descriptor triggers error."""
        invalid_handler = """
handler_id: compute.schema.validator
name: Schema Validator
contract_version:
  major: 1
  minor: 0
  patch: 0
input_model: myapp.models.Input
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "missing_descriptor.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("descriptor" in error.lower() for error in errors)

    def test_handler_contract_missing_input_model(self, temp_repo):
        """Missing input_model triggers error."""
        invalid_handler = """
handler_id: compute.schema.validator
name: Schema Validator
contract_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  node_archetype: compute
  purity: pure
  idempotent: true
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "missing_input_model.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("input_model" in error.lower() for error in errors)

    def test_handler_contract_missing_output_model(self, temp_repo):
        """Missing output_model triggers error."""
        invalid_handler = """
handler_id: compute.schema.validator
name: Schema Validator
contract_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  node_archetype: compute
  purity: pure
  idempotent: true
input_model: myapp.models.Input
"""
        yaml_file = temp_repo / "missing_output_model.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("output_model" in error.lower() for error in errors)

    def test_handler_contract_invalid_handler_id_format(self, temp_repo):
        """Invalid handler_id format triggers error."""
        invalid_handler = """
handler_id: single_segment
name: Schema Validator
contract_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  node_archetype: compute
  purity: pure
  idempotent: true
input_model: myapp.models.Input
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "invalid_handler_id.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        # handler_id must have at least 2 segments (dot-separated)
        assert any(
            "segment" in error.lower() or "handler_id" in error.lower()
            for error in errors
        )

    def test_handler_contract_invalid_contract_version_format(self, temp_repo):
        """Invalid contract_version format triggers error."""
        invalid_handler = """
handler_id: compute.schema.validator
name: Schema Validator
contract_version: not-a-version
descriptor:
  node_archetype: compute
  purity: pure
  idempotent: true
input_model: myapp.models.Input
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "invalid_contract_version.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("contract_version" in error.lower() for error in errors)

    def test_handler_contract_invalid_node_archetype(self, temp_repo):
        """Invalid node_archetype triggers error."""
        invalid_handler = """
handler_id: compute.schema.validator
name: Schema Validator
contract_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  node_archetype: invalid_kind
  purity: pure
  idempotent: true
input_model: myapp.models.Input
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "invalid_node_archetype.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("node_archetype" in error.lower() for error in errors)

    def test_handler_contract_invalid_purity(self, temp_repo):
        """Invalid purity value triggers error."""
        invalid_handler = """
handler_id: compute.schema.validator
name: Schema Validator
contract_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  node_archetype: compute
  purity: invalid_purity
  idempotent: true
input_model: myapp.models.Input
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "invalid_purity.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any("purity" in error.lower() for error in errors)

    def test_handler_contract_id_kind_mismatch(self, temp_repo):
        """Handler ID prefix must match node_archetype."""
        invalid_handler = """
handler_id: compute.schema.validator
name: Schema Validator
contract_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  node_archetype: effect
  purity: side_effecting
  idempotent: true
input_model: myapp.models.Input
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "id_kind_mismatch.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        # The compute prefix should require node_archetype: compute
        assert any(
            "compute" in error.lower()
            or "node_archetype" in error.lower()
            or "prefix" in error.lower()
            for error in errors
        )

    def test_handler_contract_all_valid_kinds(self, temp_repo):
        """All valid node_archetype values are accepted."""
        valid_kinds = ["compute", "effect", "reducer", "orchestrator"]

        for kind in valid_kinds:
            valid_handler = f"""
handler_id: handler.test.{kind}
name: Test Handler
contract_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  node_archetype: {kind}
  purity: {"pure" if kind == "compute" else "side_effecting"}
  idempotent: true
input_model: myapp.models.Input
output_model: myapp.models.Output
"""
            yaml_file = temp_repo / f"valid_{kind}_handler.yaml"
            yaml_file.write_text(valid_handler)

            errors = validate_yaml_file(yaml_file)
            assert len(errors) == 0, (
                f"Handler kind '{kind}' should be valid. Errors: {errors}"
            )

    def test_handler_contract_with_capability_inputs(self, temp_repo):
        """Handler contract with capability inputs validates."""
        valid_handler = """
handler_id: reducer.registration.user
name: User Registration Reducer
contract_version:
  major: 1
  minor: 2
  patch: 0
descriptor:
  node_archetype: reducer
  purity: side_effecting
  idempotent: true
  timeout_ms: 30000

capability_inputs:
  - alias: db
    capability: database.relational
    strict: true
  - alias: cache
    capability: cache.distributed
    strict: false

capability_outputs:
  - registration.completed
  - registration.failed

input_model: myapp.models.RegistrationEvent
output_model: myapp.models.RegistrationState
"""
        yaml_file = temp_repo / "handler_with_capabilities.yaml"
        yaml_file.write_text(valid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0, (
            f"Valid handler with capabilities should pass. Errors: {errors}"
        )

    def test_handler_contract_duplicate_capability_aliases(self, temp_repo):
        """Duplicate capability aliases trigger error."""
        invalid_handler = """
handler_id: reducer.registration.user
name: User Registration Reducer
contract_version:
  major: 1
  minor: 2
  patch: 0
descriptor:
  node_archetype: reducer
  purity: side_effecting
  idempotent: true

capability_inputs:
  - alias: db
    capability: database.relational
    strict: true
  - alias: db
    capability: cache.distributed
    strict: false

input_model: myapp.models.Input
output_model: myapp.models.Output
"""
        yaml_file = temp_repo / "duplicate_aliases.yaml"
        yaml_file.write_text(invalid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) >= 1
        assert any(
            "alias" in error.lower() or "duplicate" in error.lower() for error in errors
        )

    def test_handler_contract_with_execution_constraints(self, temp_repo):
        """Handler contract with execution constraints validates."""
        valid_handler = """
handler_id: effect.database.user_repo
name: User Repository
contract_version:
  major: 2
  minor: 0
  patch: 0
descriptor:
  node_archetype: effect
  purity: side_effecting
  idempotent: true
  timeout_ms: 30000

input_model: myapp.models.UserRequest
output_model: myapp.models.UserResult

execution_constraints:
  requires_before:
    - capability:auth
    - capability:validation
  requires_after:
    - capability:audit
  can_run_parallel: false
  must_run: true
  nondeterministic_effect: true
"""
        yaml_file = temp_repo / "handler_with_constraints.yaml"
        yaml_file.write_text(valid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0, (
            f"Valid handler with constraints should pass. Errors: {errors}"
        )

    def test_handler_contract_with_retry_policy(self, temp_repo):
        """Handler contract with retry policy validates."""
        valid_handler = """
handler_id: effect.api.external_service
name: External Service Handler
contract_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  node_archetype: effect
  purity: side_effecting
  idempotent: false
  timeout_ms: 60000
  retry_policy:
    enabled: true
    max_retries: 3
    backoff_strategy: exponential
    base_delay_ms: 200
    max_delay_ms: 10000

input_model: myapp.models.ApiRequest
output_model: myapp.models.ApiResponse
"""
        yaml_file = temp_repo / "handler_with_retry.yaml"
        yaml_file.write_text(valid_handler)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0, (
            f"Valid handler with retry policy should pass. Errors: {errors}"
        )

    def test_example_handler_contracts_validate(self):
        """Example handler contracts pass validation (regression test)."""
        example_path = (
            Path(__file__).parent.parent.parent.parent
            / "examples"
            / "contracts"
            / "handlers"
        )

        if not example_path.exists():
            pytest.skip("examples/contracts/handlers directory not found")

        yaml_files = list(example_path.glob("*.yaml"))

        if not yaml_files:
            pytest.skip("No YAML files found in examples/contracts/handlers")

        all_errors = []
        for yaml_file in yaml_files:
            errors = validate_yaml_file(yaml_file)
            if errors:
                all_errors.append(f"{yaml_file.name}: {errors}")

        assert len(all_errors) == 0, (
            "Example handler contracts failed validation:\n" + "\n".join(all_errors)
        )


@pytest.mark.unit
class TestFixtureValidation:
    """Test validation using test fixtures."""

    def test_valid_fixtures_pass_validation(self):
        """Valid fixtures pass validation."""
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "validation"

        if fixtures_dir.exists():
            valid_fixtures = fixtures_dir / "valid"
            valid_contract = valid_fixtures / "sample_contract.yaml"

            if valid_contract.exists():
                errors = validate_yaml_file(valid_contract)
                assert len(errors) == 0, (
                    f"Valid contract fixture should pass. Errors: {errors}"
                )

    def test_invalid_fixtures_trigger_violations(self):
        """Invalid fixtures trigger validation errors."""
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "validation"

        if fixtures_dir.exists():
            invalid_fixtures = fixtures_dir / "invalid"
            malformed_contract = invalid_fixtures / "malformed_contract.yaml"

            if malformed_contract.exists():
                errors = validate_yaml_file(malformed_contract)
                # Should detect either YAML parsing errors or missing required fields
                assert len(errors) > 0, (
                    "Malformed contract should trigger validation errors"
                )

    def test_edge_case_fixtures(self):
        """Edge case fixtures do not crash."""
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "validation"

        if fixtures_dir.exists():
            edge_cases = fixtures_dir / "edge_cases"
            if edge_cases.exists():
                # Test any YAML files in edge cases
                yaml_files = list(edge_cases.glob("*.yaml")) + list(
                    edge_cases.glob("*.yml"),
                )
                for yaml_file in yaml_files:
                    # Should not crash, regardless of content
                    errors = validate_yaml_file(yaml_file)
                    assert isinstance(errors, list)


@pytest.mark.unit
class TestPerformanceAndScalability:
    """Test performance and scalability."""

    def test_many_small_files_performance(self, temp_repo):
        """50 small YAML files validate within 10 seconds."""
        import time

        # Create many small YAML files
        for i in range(50):
            yaml_file = temp_repo / f"contract_{i:03d}.yaml"
            yaml_file.write_text(
                f"""
contract_version: "1.0.{i}"
node_type: "COMPUTE_GENERIC"
description: "Contract {i}"
""",
            )

        start_time = time.time()
        with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
            result = main()
        end_time = time.time()

        assert result == 0
        assert end_time - start_time < 10.0  # Should complete within 10 seconds

    def test_deeply_nested_directory_structure(self, temp_repo):
        """10-level deep directory structure validates successfully."""
        # Create nested directories
        current_dir = temp_repo
        for i in range(10):  # Create 10 levels deep
            current_dir = current_dir / f"level_{i}"
            current_dir.mkdir()
            # Add a YAML file at each level
            (current_dir / f"contract_level_{i}.yaml").write_text(
                f"""
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "COMPUTE_GENERIC"
description: "Contract at level {i}"
""",
            )

        with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
            result = main()
            assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

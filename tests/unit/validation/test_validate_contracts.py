#!/usr/bin/env python3
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

import pytest

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


class TestYAMLValidation:
    """Test cases for YAML file validation."""

    def test_valid_yaml_contract(self, temp_repo):
        """Test validation of a valid YAML contract."""
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
        """Test detection of missing contract_version field."""
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
        """Test detection of missing node_type field."""
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
        """Test detection when both required fields are missing."""
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
        """Test handling of empty YAML files."""
        yaml_file = temp_repo / "empty.yaml"
        yaml_file.touch()

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0  # Empty files should be OK

    def test_yaml_with_only_whitespace(self, temp_repo):
        """Test handling of YAML files with only whitespace."""
        yaml_file = temp_repo / "whitespace.yaml"
        yaml_file.write_text("   \n\n  \t  \n")

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 0  # Whitespace-only files should be OK

    def test_malformed_yaml_syntax(self, temp_repo):
        """Test handling of malformed YAML syntax."""
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
        """Test handling of YAML files with Unicode content."""
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
        """Test handling of YAML files that are not contracts."""
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
        """Test YAML with only contract_version (missing node_type)."""
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
        """Test YAML with only node_type (missing contract_version)."""
        partial_yaml = """
node_type: "EFFECT_GENERIC"
description: "Partial contract"
"""
        yaml_file = temp_repo / "partial_contract2.yaml"
        yaml_file.write_text(partial_yaml)

        errors = validate_yaml_file(yaml_file)
        assert len(errors) == 1
        assert "contract_version" in errors[0]


class TestFileHandling:
    """Test file handling edge cases."""

    def test_nonexistent_file(self):
        """Test handling of non-existent files."""
        nonexistent_file = Path("/nonexistent/file.yaml")
        errors = validate_yaml_file(nonexistent_file)

        assert len(errors) >= 1
        assert any("not exist" in error for error in errors)

    def test_directory_instead_of_file(self, temp_repo):
        """Test handling when a directory is passed instead of file."""
        test_dir = temp_repo / "test_directory"
        test_dir.mkdir()

        errors = validate_yaml_file(test_dir)
        assert len(errors) >= 1
        assert any("not a regular file" in error for error in errors)

    def test_large_yaml_file(self, temp_repo):
        """Test handling of large YAML files."""
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
        """Test rejection of extremely large files."""
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
        """Test handling of permission denied errors."""
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
        """Test handling of encoding errors."""
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
        """Test handling of OS errors."""
        yaml_file = temp_repo / "test.yaml"
        yaml_file.write_text("test: value")

        # Patch the open call to trigger the OS error handling path
        with patch("builtins.open", side_effect=OSError("OS Error")):
            errors = validate_yaml_file(yaml_file)
            assert len(errors) >= 1
            # Check for OS/IO error in message (script uses "OS/IO error reading file")
            assert any("error reading file" in error.lower() for error in errors)


class TestMainFunction:
    """Test the main function and CLI interface."""

    def test_main_with_valid_yaml_files(self, temp_repo):
        """Test main function with valid YAML files."""
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
        """Test main function with invalid YAML files."""
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
        """Test main function with directory containing no YAML files."""
        # Create non-YAML files
        (temp_repo / "test.py").write_text("print('test')")
        (temp_repo / "README.md").write_text("# Test")

        with patch("sys.argv", ["validate-contracts.py", str(temp_repo)]):
            result = main()
            assert result == 0  # Should succeed with message about no files

    def test_main_with_nonexistent_path(self):
        """Test main function with non-existent path."""
        with patch("sys.argv", ["validate-contracts.py", "/nonexistent/path"]):
            result = main()
            assert result == 1

    def test_main_with_malformed_yaml(self, temp_repo):
        """Test main function with malformed YAML."""
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
        """Test main function with argument parsing errors."""
        with patch("sys.argv", ["validate-contracts.py", "--invalid-flag"]):
            result = main()
            assert result == 2  # argparse returns 2 for argument parsing errors

    def test_main_with_archived_files_filtering(self, temp_repo):
        """Test that archived files are properly filtered out."""
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


class TestTimeoutHandling:
    """Test timeout handling functionality."""

    @pytest.mark.skipif(os.name == "nt", reason="Signal handling different on Windows")
    def test_timeout_handler_setup(self):
        """Test that timeout handler can be set up."""
        setup_timeout_handler()
        # Should not raise exception
        assert signal.signal(signal.SIGALRM, signal.SIG_DFL) is not None

    @pytest.mark.skipif(os.name == "nt", reason="Signal handling different on Windows")
    def test_file_discovery_timeout_simulation(self, temp_repo):
        """Test file discovery timeout handling."""
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


class TestErrorRecovery:
    """Test error recovery and graceful handling."""

    def test_keyboard_interrupt_handling(self, temp_repo):
        """Test handling of keyboard interrupt."""
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
        """Test handling of unexpected exceptions."""
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
        """Test that processing continues after individual file errors."""
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


class TestExampleContractsValidation:
    """Regression tests for example contracts in the repository."""

    def test_example_contracts_validate(self):
        """Validate all example contracts against the ONEX contract schema.

        Ensures example contracts pass full schema validation (node_type enum,
        required fields, structural correctness) since they serve as templates.

        Regression Prevention (OMN-539):
            Added after example contracts drifted out of schema compliance.

        Failure Means:
            - Invalid node_type, missing required fields, or schema violations
            - Fix the contract or update schema if it represents a valid pattern

        Related: test_example_contracts_have_required_fields
        """
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
        """Verify example contracts contain mandatory contract_version and node_type.

        Fast structural check using direct YAML parsing (not Pydantic) to catch
        common authoring mistakes before full schema validation.

        Regression Prevention (OMN-539):
            Catches missing required fields early, before confusing validation errors.

        Failure Means:
            - Missing contract_version or node_type in a contract file
            - Add the missing field to resolve

        Notes: Skips empty files and non-mapping YAML; uses yaml.safe_load.
        Related: test_example_contracts_validate
        """
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

            # Check if this looks like a contract (has contract indicators)
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


class TestFixtureValidation:
    """Test validation using our test fixtures."""

    def test_valid_fixtures_pass_validation(self):
        """Test that valid fixtures pass YAML validation."""
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
        """Test that invalid fixtures trigger YAML violations."""
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
        """Test edge case fixtures."""
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


class TestPerformanceAndScalability:
    """Test performance and scalability aspects."""

    def test_many_small_files_performance(self, temp_repo):
        """Test performance with many small YAML files."""
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
        """Test with deeply nested directory structures."""
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

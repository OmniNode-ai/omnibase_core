#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

"""
Comprehensive tests for repository structure validation.

Tests all aspects of the OmniStructureValidator including:
- Valid repository structures
- Invalid structures that should trigger violations
- Edge cases and error conditions
- Performance with large directory structures
"""

import shutil

# Import the validation module
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent.parent / "scripts" / "validation"),
)
from validate_structure import (
    OmniStructureValidator,
    StructureViolation,
    ViolationLevel,
    main,
    print_validation_report,
)


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)

    # Create basic repository structure
    (repo_path / "src" / "omnibase_core").mkdir(parents=True)
    (repo_path / "tests").mkdir()
    (repo_path / "docs").mkdir()

    # Create configuration files
    (repo_path / "pyproject.toml").touch()
    (repo_path / "README.md").touch()
    (repo_path / ".gitignore").touch()

    yield repo_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def minimal_repo():
    """Create a minimal repository for testing missing structure."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    yield repo_path
    shutil.rmtree(temp_dir)


@pytest.mark.unit
class TestOmniStructureValidator:
    """Test cases for OmniStructureValidator."""

    def test_valid_repository_structure(self, temp_repo):
        """Test validation of a properly structured repository."""
        # Create a valid structure
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir()
        (models_dir / "model_user_auth.py").touch()

        enums_dir = temp_repo / "src" / "omnibase_core" / "enums"
        enums_dir.mkdir()
        (enums_dir / "enum_status.py").touch()

        # Create test directories
        (temp_repo / "tests" / "unit").mkdir(parents=True)
        (temp_repo / "tests" / "integration").mkdir()

        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()

        # Should have minimal or no violations for a valid structure
        error_violations = [v for v in violations if v.level == ViolationLevel.ERROR]
        assert len(error_violations) == 0, f"Unexpected errors: {error_violations}"

    def test_missing_required_directories(self, minimal_repo):
        """Test detection of missing required directories."""
        validator = OmniStructureValidator(str(minimal_repo), "omnibase_core")
        violations = validator.validate_all()

        # Should detect missing src, tests, docs directories
        violation_messages = [v.message for v in violations]

        assert any(
            "Missing required directory: src" in msg for msg in violation_messages
        )
        assert any(
            "Missing required directory: tests" in msg for msg in violation_messages
        )
        assert any(
            "Missing required directory: docs" in msg for msg in violation_messages
        )

    def test_forbidden_directory_detection(self, temp_repo):
        """Test detection of forbidden singular directory names."""
        src_path = temp_repo / "src" / "omnibase_core"

        # Create forbidden directories
        (src_path / "model").mkdir()  # Should be "models"
        (src_path / "enum").mkdir()  # Should be "enums"
        (src_path / "protocol").mkdir()  # Should be "protocols"

        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()

        error_violations = [v for v in violations if v.level == ViolationLevel.ERROR]
        forbidden_violations = [
            v for v in error_violations if v.category == "Forbidden Directory"
        ]

        assert len(forbidden_violations) >= 3
        assert any("model" in v.message for v in forbidden_violations)
        assert any("enum" in v.message for v in forbidden_violations)
        assert any("protocol" in v.message for v in forbidden_violations)

    def test_scattered_models_detection(self, temp_repo):
        """Test detection of models directories outside the root."""
        src_path = temp_repo / "src" / "omnibase_core"

        # Create scattered model directories
        (src_path / "services" / "models").mkdir(parents=True)
        (src_path / "nodes" / "models").mkdir(parents=True)

        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()

        scattered_violations = [
            v for v in violations if v.category == "Scattered Models"
        ]
        assert len(scattered_violations) >= 2

    def test_model_file_naming_validation(self, temp_repo):
        """Test validation of model file naming conventions."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir()

        # Create files with correct and incorrect naming
        (models_dir / "model_user_auth.py").touch()  # Correct
        (models_dir / "user_data.py").touch()  # Incorrect - missing "model_" prefix
        (models_dir / "__init__.py").touch()  # Should be ignored

        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()

        naming_violations = [v for v in violations if v.category == "Model Naming"]
        assert len(naming_violations) == 1
        assert "user_data.py" in naming_violations[0].message

    def test_enum_file_naming_validation(self, temp_repo):
        """Test validation of enum file naming conventions."""
        enums_dir = temp_repo / "src" / "omnibase_core" / "enums"
        enums_dir.mkdir()

        # Create files with correct and incorrect naming
        (enums_dir / "enum_status.py").touch()  # Correct
        (enums_dir / "workflow_types.py").touch()  # Incorrect - missing "enum_" prefix

        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()

        naming_violations = [v for v in violations if v.category == "Enum Naming"]
        assert len(naming_violations) == 1
        assert "workflow_types.py" in naming_violations[0].message

    def test_protocol_location_validation_non_spi(self, temp_repo):
        """Test that non-SPI/non-core repositories shouldn't have protocols directory.

        Note: v0.3.6+ allows both omnibase_spi and omnibase_core to have protocols
        due to dependency inversion (SPI now depends on Core, not vice versa).
        Only other repositories should trigger violations.
        """
        # Use a third-party repo name that's NOT in PROTOCOL_ALLOWED_REPOS
        other_repo_path = temp_repo / "src" / "omnibase_other"
        other_repo_path.mkdir(parents=True)
        (other_repo_path / "protocols").mkdir()

        validator = OmniStructureValidator(str(temp_repo), "omnibase_other")
        violations = validator.validate_all()

        protocol_violations = [
            v for v in violations if v.category == "Protocol Location"
        ]
        assert len(protocol_violations) == 1
        assert "omnibase_spi" in protocol_violations[0].message

    def test_protocol_location_validation_core_repo(self, temp_repo):
        """Test that omnibase_core repository is allowed to have protocols (v0.3.6+)."""
        src_path = temp_repo / "src" / "omnibase_core"
        (src_path / "protocols").mkdir()

        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()

        protocol_violations = [
            v for v in violations if v.category == "Protocol Location"
        ]
        assert len(protocol_violations) == 0

    def test_protocol_location_validation_spi_repo(self, temp_repo):
        """Test that omnibase_spi repository is allowed to have protocols."""
        src_path = temp_repo / "src" / "omnibase_spi"
        src_path.mkdir()
        (src_path / "protocols").mkdir()

        validator = OmniStructureValidator(str(temp_repo), "omnibase_spi")
        violations = validator.validate_all()

        protocol_violations = [
            v for v in violations if v.category == "Protocol Location"
        ]
        assert len(protocol_violations) == 0

    def test_node_structure_validation(self, temp_repo):
        """Test validation of ONEX four-node architecture."""
        src_path = temp_repo / "src" / "omnibase_core"
        nodes_dir = src_path / "nodes"
        nodes_dir.mkdir()

        # Create valid node structure
        valid_node = nodes_dir / "node_user_compute"
        valid_node.mkdir()
        (valid_node / "v1_0_0").mkdir()
        (valid_node / "v1_0_0" / "node.py").touch()

        # Create invalid node structure (missing prefix)
        invalid_node = nodes_dir / "user_processor"
        invalid_node.mkdir()

        # Create node with invalid suffix
        invalid_suffix_node = nodes_dir / "node_data_processor"  # Missing type suffix
        invalid_suffix_node.mkdir()

        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()

        node_violations = [v for v in violations if "Node" in v.category]
        assert len(node_violations) >= 2  # Should catch naming and type suffix issues

    def test_test_structure_validation(self, temp_repo):
        """Test validation of test directory structure."""
        # Don't create test subdirectories to trigger warnings
        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()

        test_violations = [v for v in violations if v.category == "Test Organization"]
        assert (
            len(test_violations) >= 2
        )  # Should warn about missing unit and integration dirs

    def test_missing_files_validation(self, minimal_repo):
        """Test detection of missing recommended files."""
        # Create minimal structure to avoid other errors
        (minimal_repo / "src" / "omnibase_core").mkdir(parents=True)

        validator = OmniStructureValidator(str(minimal_repo), "omnibase_core")
        violations = validator.validate_all()

        file_violations = [v for v in violations if v.category == "Missing File"]
        file_messages = [v.message for v in file_violations]

        assert any("pyproject.toml" in msg for msg in file_messages)
        assert any("README.md" in msg for msg in file_messages)
        assert any(".gitignore" in msg for msg in file_messages)

    def test_model_domain_organization_validation(self, temp_repo):
        """Test validation of model organization by domain."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir()

        # Don't create domain subdirectories to trigger warning
        (models_dir / "model_user.py").touch()

        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()

        organization_violations = [
            v for v in violations if v.category == "Model Organization"
        ]
        assert len(organization_violations) >= 1


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_repository_path(self):
        """Test behavior with empty repository path."""
        # Empty path should resolve to current directory
        validator = OmniStructureValidator("", "omnibase_core")
        violations = validator.validate_all()

        # Should complete without raising exceptions
        # May have violations depending on current directory structure
        assert isinstance(violations, list)

    def test_nonexistent_repository_path(self):
        """Test behavior with non-existent repository path."""
        validator = OmniStructureValidator("/nonexistent/path", "omnibase_core")
        violations = validator.validate_all()

        # Should generate violations about missing directories
        assert len(violations) > 0

    def test_invalid_repository_name(self, temp_repo):
        """Test behavior with invalid repository name."""
        validator = OmniStructureValidator(str(temp_repo), "")
        violations = validator.validate_all()

        # Should still work but may generate path-related violations
        assert isinstance(violations, list)

    @patch("os.walk")
    def test_permission_error_handling(self, mock_walk, temp_repo):
        """Test handling of permission errors during directory traversal."""
        mock_walk.side_effect = PermissionError("Permission denied")

        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        # Should not raise exception, but may log errors
        violations = validator.validate_all()
        assert isinstance(violations, list)

    def test_large_directory_structure_performance(self, temp_repo):
        """Test performance with large directory structures."""
        import time

        # Create many directories and files
        src_path = temp_repo / "src" / "omnibase_core"
        models_dir = src_path / "models"
        models_dir.mkdir()

        # Create 100 model files to test performance
        for i in range(100):
            (models_dir / f"model_test_{i:03d}.py").touch()

        start_time = time.time()
        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()
        end_time = time.time()

        # Should complete within reasonable time (less than 5 seconds)
        assert end_time - start_time < 5.0
        assert isinstance(violations, list)


@pytest.mark.unit
class TestReportGeneration:
    """Test validation report generation."""

    def test_print_validation_report_success(self, capsys):
        """Test report printing for successful validation."""
        violations = []
        success = print_validation_report(violations, "test_repo")

        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out
        assert success is True

    def test_print_validation_report_with_violations(self, capsys):
        """Test report printing with violations."""
        violations = [
            StructureViolation(
                level=ViolationLevel.ERROR,
                category="Test Category",
                message="Test error message",
                path="test/path",
                suggestion="Test suggestion",
            ),
            StructureViolation(
                level=ViolationLevel.WARNING,
                category="Test Category",
                message="Test warning message",
                path="test/path",
                suggestion="Test suggestion",
            ),
        ]

        success = print_validation_report(violations, "test_repo")

        captured = capsys.readouterr()
        assert "FAILURE" in captured.out
        assert "Test error message" in captured.out
        assert "Test warning message" in captured.out
        assert success is False

    def test_report_violation_grouping(self, capsys):
        """Test that violations are properly grouped by category in reports."""
        violations = [
            StructureViolation(
                level=ViolationLevel.ERROR,
                category="Category A",
                message="Message 1",
                path="path1",
                suggestion="Suggestion 1",
            ),
            StructureViolation(
                level=ViolationLevel.ERROR,
                category="Category A",
                message="Message 2",
                path="path2",
                suggestion="Suggestion 2",
            ),
            StructureViolation(
                level=ViolationLevel.WARNING,
                category="Category B",
                message="Message 3",
                path="path3",
                suggestion="Suggestion 3",
            ),
        ]

        print_validation_report(violations, "test_repo")
        captured = capsys.readouterr()

        # Should show both categories
        assert "Category A" in captured.out
        assert "Category B" in captured.out
        assert "Message 1" in captured.out
        assert "Message 2" in captured.out
        assert "Message 3" in captured.out


@pytest.mark.unit
class TestMainFunction:
    """Test the main function and CLI interface."""

    def test_main_with_valid_arguments(self, temp_repo):
        """Test main function with valid arguments."""
        with patch(
            "sys.argv",
            ["validate_structure.py", str(temp_repo), "omnibase_core"],
        ):
            try:
                result = main()
                # Should complete without exception
                assert result in [0, 1]  # Valid exit codes
            except SystemExit as e:
                assert e.code in [0, 1]

    def test_main_with_json_output(self, temp_repo):
        """Test main function with JSON output format."""
        # Create a violation to ensure JSON output
        (temp_repo / "src" / "omnibase_core" / "model").mkdir(
            parents=True,
        )  # Forbidden directory

        with patch(
            "sys.argv",
            ["validate_structure.py", str(temp_repo), "omnibase_core", "--json"],
        ):
            with patch("builtins.print") as mock_print:
                try:
                    main()
                except SystemExit:
                    pass

                # Should have printed JSON output
                printed_args = [call.args[0] for call in mock_print.call_args_list]
                json_output = "".join(str(arg) for arg in printed_args)

                # Basic check that JSON-like content was printed
                assert "[" in json_output or "{" in json_output

    def test_main_with_missing_arguments(self):
        """Test main function with missing required arguments."""
        with patch("sys.argv", ["validate_structure.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0


@pytest.mark.unit
class TestFixtureValidation:
    """Test validation using our test fixtures."""

    def test_valid_fixtures_pass_validation(self):
        """Test that valid fixtures pass structure validation."""
        # This would need the actual fixture files to be in a proper repo structure
        # For now, just test that the concept works
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "validation"

        if fixtures_dir.exists():
            # Create a temporary repo structure with valid files
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = Path(temp_dir)
                src_path = repo_path / "src" / "omnibase_core"
                src_path.mkdir(parents=True)

                # Copy valid fixtures to proper locations
                models_dir = src_path / "models"
                models_dir.mkdir()

                valid_model = fixtures_dir / "valid" / "model_user_auth.py"
                if valid_model.exists():
                    shutil.copy(valid_model, models_dir / "model_user_auth.py")

                validator = OmniStructureValidator(str(repo_path), "omnibase_core")
                violations = validator.validate_all()

                # Should have minimal violations for properly structured valid files
                error_violations = [
                    v for v in violations if v.level == ViolationLevel.ERROR
                ]
                model_naming_errors = [
                    v for v in error_violations if v.category == "Model Naming"
                ]
                assert len(model_naming_errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

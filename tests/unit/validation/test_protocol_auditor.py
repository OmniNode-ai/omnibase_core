"""
Tests for ProtocolAuditor class.

Tests protocol auditing functionality including initialization validation,
error handling, and audit operations.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.validation import (
    ConfigurationError,
    ModelProtocolAuditor,
)


class TestProtocolAuditorInitialization:
    """Test ProtocolAuditor initialization and validation."""

    def test_init_with_valid_directory(self):
        """Test initialization with valid repository directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch(
                "omnibase_core.validation.auditor_protocol.logger",
            ) as mock_logger:
                auditor = ModelProtocolAuditor(str(temp_path))

                assert auditor.repository_path == temp_path.resolve()
                assert auditor.repository_name is not None

                # Should log initialization
                mock_logger.info.assert_called_once()
                call_args = mock_logger.info.call_args[0][0]
                assert "initialized" in call_args.lower()
                assert "repository" in call_args.lower()

    def test_init_with_nonexistent_directory(self):
        """Test initialization fails with nonexistent directory."""
        nonexistent_path = "/nonexistent/repository"

        with pytest.raises(
            ConfigurationError,
            match="Invalid repository configuration",
        ):
            ModelProtocolAuditor(nonexistent_path)

    def test_init_with_file_instead_of_directory(self):
        """Test initialization fails when file is passed instead of directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_path = temp_file.name

            with pytest.raises(
                ConfigurationError,
                match="Invalid repository configuration",
            ):
                ModelProtocolAuditor(temp_path)

    def test_init_with_current_directory(self):
        """Test initialization with current directory (default)."""
        # This should work since we're running from a valid directory
        auditor = ModelProtocolAuditor()

        assert auditor.repository_path.exists()
        assert auditor.repository_path.is_dir()

    def test_init_with_relative_path(self):
        """Test initialization with relative path."""
        # Use current directory's parent as a relative path
        with patch("omnibase_core.validation.auditor_protocol.logger"):
            auditor = ModelProtocolAuditor(".")

            assert auditor.repository_path.is_absolute()
            assert auditor.repository_path.exists()


class TestProtocolAuditorValidation:
    """Test ProtocolAuditor validation methods."""

    def test_check_against_spi_with_invalid_path(self):
        """Test check_against_spi fails with invalid SPI path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auditor = ModelProtocolAuditor(temp_dir)
            invalid_spi_path = "/nonexistent/spi/path"

            with pytest.raises(
                ConfigurationError,
                match="Invalid SPI path configuration",
            ):
                auditor.check_against_spi(invalid_spi_path)

    def test_check_against_spi_with_valid_path_missing_protocols(self):
        """Test check_against_spi handles missing protocols directory gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with tempfile.TemporaryDirectory() as spi_dir:
                auditor = ModelProtocolAuditor(temp_dir)

                with patch(
                    "omnibase_core.validation.auditor_protocol.logger",
                ) as mock_logger:
                    # This should not raise an exception, just log a warning
                    result = auditor.check_against_spi(spi_dir)

                    assert result is not None
                    # Should warn about missing SPI protocols directory
                    mock_logger.warning.assert_called_once()
                    call_args = mock_logger.warning.call_args[0][0]
                    assert "spi protocols directory not found" in call_args.lower()


class TestProtocolAuditorFunctional:
    """Functional tests for ProtocolAuditor operations."""

    def create_protocol_file(
        self,
        directory: Path,
        filename: str,
        protocol_name: str,
        methods: list,
    ):
        """Helper to create a protocol file for testing."""
        protocol_code = f"""
from typing import Protocol

class {protocol_name}(Protocol):
"""
        for method in methods:
            protocol_code += f"""    def {method}(self) -> str:
        ...

"""

        protocol_file = directory / filename
        protocol_file.write_text(protocol_code)
        return protocol_file

    def test_check_current_repository_empty(self):
        """Test auditing empty repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auditor = ModelProtocolAuditor(temp_dir)
            result = auditor.check_current_repository()

            assert result is not None
            assert result.repository == auditor.repository_name
            assert result.protocols_found == 0

    def test_check_current_repository_with_protocols(self):
        """Test auditing repository with protocol files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            src_path = temp_path / "src"
            src_path.mkdir()

            # Create a protocol file
            self.create_protocol_file(
                src_path,
                "test_protocol.py",
                "TestProtocol",
                ["method_one", "method_two"],
            )

            auditor = ModelProtocolAuditor(temp_dir)
            result = auditor.check_current_repository()

            assert result is not None
            assert result.protocols_found == 1
            assert result.repository == auditor.repository_name

    def test_check_current_repository_with_duplicates(self):
        """Test auditing repository with duplicate protocols."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            src_path = temp_path / "src"
            src_path.mkdir()

            # Create two identical protocol files
            self.create_protocol_file(
                src_path,
                "protocol_a.py",
                "DuplicateProtocol",
                ["identical_method"],
            )
            self.create_protocol_file(
                src_path,
                "protocol_b.py",
                "DuplicateProtocol",
                ["identical_method"],
            )

            auditor = ModelProtocolAuditor(temp_dir)
            result = auditor.check_current_repository()

            assert result is not None
            assert result.protocols_found == 2
            assert result.duplicates_found > 0
            assert not result.success  # Should fail due to duplicates
            assert len(result.violations) > 0

    @patch("omnibase_core.validation.auditor_protocol.extract_protocols_from_directory")
    def test_audit_handles_extraction_errors(self, mock_extract):
        """Test auditing handles protocol extraction errors gracefully."""
        mock_extract.side_effect = Exception("Extraction failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create src directory to avoid early return
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()

            auditor = ModelProtocolAuditor(temp_dir)

            # Should raise the extraction exception since we don't handle it gracefully yet
            with pytest.raises(Exception, match="Extraction failed"):
                auditor.check_current_repository()


class TestProtocolAuditorLogging:
    """Test ProtocolAuditor logging behavior."""

    def test_initialization_logging(self):
        """Test that auditor initialization is logged."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "omnibase_core.validation.auditor_protocol.logger",
            ) as mock_logger:
                auditor = ModelProtocolAuditor(temp_dir)

                mock_logger.info.assert_called_once()
                call_args = mock_logger.info.call_args[0][0]
                assert "ProtocolAuditor initialized" in call_args
                assert auditor.repository_name in call_args
                assert str(auditor.repository_path) in call_args

    def test_spi_path_validation_logging(self):
        """Test that SPI path validation issues are logged."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with tempfile.TemporaryDirectory() as spi_dir:
                auditor = ModelProtocolAuditor(temp_dir)

                with patch(
                    "omnibase_core.validation.auditor_protocol.logger",
                ) as mock_logger:
                    auditor.check_against_spi(spi_dir)

                    # Should log warning about missing SPI protocols directory
                    mock_logger.warning.assert_called_once()
                    call_args = mock_logger.warning.call_args[0][0]
                    assert "SPI protocols directory not found" in call_args


class TestProtocolAuditorEdgeCases:
    """Test edge cases and error conditions."""

    def test_audit_with_permission_denied(self):
        """Test auditing handles permission errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create src directory to avoid early return
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()

            auditor = ModelProtocolAuditor(temp_dir)

            # Mock extract_protocols_from_directory to raise a permission error
            with patch(
                "omnibase_core.validation.auditor_protocol.extract_protocols_from_directory",
            ) as mock_extract:
                mock_extract.side_effect = PermissionError("Permission denied")

                with pytest.raises(PermissionError):
                    auditor.check_current_repository()

    def test_audit_with_malformed_repository_structure(self):
        """Test auditing repository with unusual structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Don't create src directory - unusual but valid
            auditor = ModelProtocolAuditor(temp_dir)
            result = auditor.check_current_repository()

            # Should complete successfully with no protocols found
            assert result is not None
            assert result.protocols_found == 0

    def test_repository_name_determination(self):
        """Test repository name is properly determined."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a nested structure that looks like an omni* repository
            omni_repo = temp_path / "omnitest_repo"
            omni_repo.mkdir()

            auditor = ModelProtocolAuditor(str(omni_repo))

            # Repository name should be determined from path
            assert (
                "omnitest_repo" in auditor.repository_name
                or auditor.repository_name == "unknown"
            )


class TestConfigurationErrorHandling:
    """Test configuration error handling and reporting."""

    def test_configuration_error_chaining(self):
        """Test that configuration errors properly chain underlying exceptions."""
        with pytest.raises(ConfigurationError) as exc_info:
            ModelProtocolAuditor("/definitely/nonexistent/path")

        # Should contain information about the underlying validation error
        assert "Invalid repository configuration" in str(exc_info.value)

    def test_spi_configuration_error_chaining(self):
        """Test that SPI configuration errors properly chain underlying exceptions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            auditor = ModelProtocolAuditor(temp_dir)

            with pytest.raises(ConfigurationError) as exc_info:
                auditor.check_against_spi("/definitely/nonexistent/spi/path")

            assert "Invalid SPI path configuration" in str(exc_info.value)

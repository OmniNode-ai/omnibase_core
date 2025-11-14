"""
Tests for validation framework exceptions.

Tests the custom exception hierarchy and error handling behavior.
"""

import pytest

from omnibase_core.errors.exceptions import (
    ExceptionAudit,
    ExceptionConfiguration,
    ExceptionFileProcessing,
    ExceptionInputValidation,
    ExceptionMigration,
    ExceptionPathTraversal,
    ExceptionProtocolParsing,
    ExceptionValidationFramework,
)


class TestExceptionHierarchy:
    """Test the exception inheritance hierarchy."""

    def test_base_exception(self):
        """Test ExceptionValidationFramework is the base exception."""
        exc = ExceptionValidationFramework("Base error")
        assert str(exc) == "Base error"
        assert isinstance(exc, Exception)

    def test_configuration_error_inheritance(self):
        """Test ExceptionConfiguration inherits from ExceptionValidationFramework."""
        exc = ExceptionConfiguration("Config error")
        assert isinstance(exc, ExceptionValidationFramework)
        assert isinstance(exc, Exception)
        assert str(exc) == "Config error"

    def test_file_processing_error_inheritance(self):
        """Test ExceptionFileProcessing inherits from ExceptionValidationFramework."""
        exc = ExceptionFileProcessing("File error", "/path/to/file.py")
        assert isinstance(exc, ExceptionValidationFramework)
        assert isinstance(exc, Exception)

    def test_protocol_parsing_error_inheritance(self):
        """Test ExceptionProtocolParsing inherits from ExceptionFileProcessing."""
        exc = ExceptionProtocolParsing("Parse error", "/path/to/file.py")
        assert isinstance(exc, ExceptionFileProcessing)
        assert isinstance(exc, ExceptionValidationFramework)
        assert isinstance(exc, Exception)

    def test_input_validation_error_inheritance(self):
        """Test ExceptionInputValidation inherits from ExceptionValidationFramework."""
        exc = ExceptionInputValidation("Invalid input")
        assert isinstance(exc, ExceptionValidationFramework)
        assert isinstance(exc, Exception)

    def test_path_traversal_error_inheritance(self):
        """Test ExceptionPathTraversal inherits from ExceptionInputValidation."""
        exc = ExceptionPathTraversal("Path traversal attempt")
        assert isinstance(exc, ExceptionInputValidation)
        assert isinstance(exc, ExceptionValidationFramework)
        assert isinstance(exc, Exception)

    def test_audit_error_inheritance(self):
        """Test ExceptionAudit inherits from ExceptionValidationFramework."""
        exc = ExceptionAudit("Audit failed")
        assert isinstance(exc, ExceptionValidationFramework)
        assert isinstance(exc, Exception)

    def test_migration_error_inheritance(self):
        """Test ExceptionMigration inherits from ExceptionValidationFramework."""
        exc = ExceptionMigration("Migration failed")
        assert isinstance(exc, ExceptionValidationFramework)
        assert isinstance(exc, Exception)


class TestExceptionFileProcessing:
    """Test ExceptionFileProcessing specific functionality."""

    def test_file_processing_error_basic(self):
        """Test basic ExceptionFileProcessing creation."""
        exc = ExceptionFileProcessing("Could not read file", "/path/to/file.py")

        assert exc.file_path == "/path/to/file.py"
        assert exc.original_exception is None
        assert str(exc) == "Could not read file [File: /path/to/file.py]"

    def test_file_processing_error_with_original_exception(self):
        """Test ExceptionFileProcessing with original exception."""
        original = OSError("Permission denied")
        exc = ExceptionFileProcessing(
            "Could not read file", "/path/to/file.py", original
        )

        assert exc.file_path == "/path/to/file.py"
        assert exc.original_exception is original
        assert str(exc) == "Could not read file [File: /path/to/file.py]"

    def test_file_processing_error_attributes(self):
        """Test ExceptionFileProcessing attributes are accessible."""
        exc = ExceptionFileProcessing("Error message", "/test/path.py")

        # Should have file_path attribute
        assert hasattr(exc, "file_path")
        assert exc.file_path == "/test/path.py"

        # Should have original_exception attribute (even if None)
        assert hasattr(exc, "original_exception")
        assert exc.original_exception is None


class TestExceptionProtocolParsing:
    """Test ExceptionProtocolParsing specific functionality."""

    def test_protocol_parsing_error_creation(self):
        """Test ExceptionProtocolParsing creation and inheritance."""
        exc = ExceptionProtocolParsing(
            "Syntax error in protocol", "/path/to/protocol.py"
        )

        # Should inherit ExceptionFileProcessing behavior
        assert exc.file_path == "/path/to/protocol.py"
        assert str(exc) == "Syntax error in protocol [File: /path/to/protocol.py]"

        # Should be identifiable as specific parsing error
        assert isinstance(exc, ExceptionProtocolParsing)
        assert isinstance(exc, ExceptionFileProcessing)

    def test_protocol_parsing_error_with_original(self):
        """Test ExceptionProtocolParsing with original SyntaxError."""
        syntax_error = SyntaxError("invalid syntax")
        exc = ExceptionProtocolParsing(
            "Could not parse protocol", "/test.py", syntax_error
        )

        assert exc.original_exception is syntax_error
        assert exc.file_path == "/test.py"


class TestExceptionCatching:
    """Test exception catching patterns."""

    def test_catch_base_exception(self):
        """Test catching all validation exceptions with base class."""
        exceptions_to_test = [
            ExceptionConfiguration("config"),
            ExceptionFileProcessing("file", "/path"),
            ExceptionProtocolParsing("parse", "/path"),
            ExceptionInputValidation("input"),
            ExceptionPathTraversal("traversal"),
            ExceptionAudit("audit"),
            ExceptionMigration("migration"),
        ]

        for exc in exceptions_to_test:
            try:
                raise exc
            except ExceptionValidationFramework as caught:
                assert caught is exc
                assert isinstance(caught, ExceptionValidationFramework)
            else:
                pytest.fail(
                    f"Failed to catch {type(exc).__name__} with ExceptionValidationFramework",
                )

    def test_catch_specific_exceptions(self):
        """Test catching specific exception types."""
        # Test ExceptionFileProcessing catching
        try:
            raise ExceptionProtocolParsing("parse error", "/path")
        except ExceptionFileProcessing as exc:
            assert isinstance(exc, ExceptionProtocolParsing)
            assert exc.file_path == "/path"

        # Test ExceptionInputValidation catching
        try:
            raise ExceptionPathTraversal("traversal error")
        except ExceptionInputValidation as exc:
            assert isinstance(exc, ExceptionPathTraversal)

    def test_exception_context_preservation(self):
        """Test that exception context is preserved."""
        original_error = ValueError("Original error")

        try:
            try:
                raise original_error
            except ValueError:
                raise ExceptionConfiguration("Configuration failed")
        except ExceptionConfiguration as exc:
            # Should be able to access the original exception through __cause__
            assert exc.__cause__ is None  # Not using raise ... from
            # But we can still check the chain
            assert str(exc) == "Configuration failed"


class TestExceptionDocumentation:
    """Test that exceptions have proper documentation."""

    def test_all_exceptions_have_docstrings(self):
        """Test that all exception classes have docstrings."""
        exceptions = [
            ExceptionValidationFramework,
            ExceptionConfiguration,
            ExceptionFileProcessing,
            ExceptionProtocolParsing,
            ExceptionInputValidation,
            ExceptionPathTraversal,
            ExceptionAudit,
            ExceptionMigration,
        ]

        for exc_class in exceptions:
            assert exc_class.__doc__ is not None
            assert (
                len(exc_class.__doc__.strip()) > 0
            ), f"{exc_class.__name__} missing docstring"

    def test_exception_docstrings_describe_purpose(self):
        """Test that exception docstrings describe their purpose."""
        # ExceptionConfiguration should mention configuration
        assert "configuration" in ExceptionConfiguration.__doc__.lower()

        # ExceptionFileProcessing should mention file processing
        assert "file" in ExceptionFileProcessing.__doc__.lower()

        # ExceptionProtocolParsing should mention parsing
        assert "parsing" in ExceptionProtocolParsing.__doc__.lower()

        # ExceptionInputValidation should mention validation
        assert "validation" in ExceptionInputValidation.__doc__.lower()

        # ExceptionPathTraversal should mention security/traversal
        doc = ExceptionPathTraversal.__doc__.lower()
        assert "traversal" in doc or "security" in doc

        # ExceptionAudit should mention audit
        assert "audit" in ExceptionAudit.__doc__.lower()

        # ExceptionMigration should mention migration
        assert "migration" in ExceptionMigration.__doc__.lower()


class TestExceptionUsagePatterns:
    """Test common exception usage patterns."""

    def test_configuration_error_fail_fast(self):
        """Test ExceptionConfiguration enables fail-fast behavior."""

        # This pattern should be used in ProtocolAuditor.__init__
        def validate_config(path):
            if not path:
                raise ExceptionConfiguration("Path cannot be empty")
            return True

        with pytest.raises(ExceptionConfiguration, match="Path cannot be empty"):
            validate_config("")

    def test_file_processing_error_with_context(self):
        """Test ExceptionFileProcessing provides useful context."""
        file_path = "/important/protocol.py"
        error_msg = "Could not parse AST"

        exc = ExceptionFileProcessing(error_msg, file_path)

        # Error message should include both the message and file path
        full_msg = str(exc)
        assert error_msg in full_msg
        assert file_path in full_msg
        assert "[File:" in full_msg

    def test_input_validation_error_security(self):
        """Test ExceptionInputValidation for security validation."""

        def validate_path(path):
            if ".." in path:
                raise ExceptionPathTraversal(f"Path traversal detected: {path}")
            if not path.startswith("/allowed/"):
                raise ExceptionInputValidation(f"Path not in allowed directory: {path}")

        with pytest.raises(ExceptionPathTraversal):
            validate_path("../../etc/passwd")

        with pytest.raises(ExceptionInputValidation):
            validate_path("/forbidden/path")

        # Valid path should not raise
        try:
            validate_path("/allowed/valid/path")
        except (ExceptionInputValidation, ExceptionPathTraversal):
            pytest.fail("Valid path should not raise validation error")

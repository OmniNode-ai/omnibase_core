"""
Tests for validation framework exceptions.

Tests the custom exception hierarchy and error handling behavior.
"""

import pytest

from omnibase_core.errors.exceptions import (
    ExceptionAuditError,
    ExceptionConfigurationError,
    ExceptionFileProcessingError,
    ExceptionInputValidationError,
    ExceptionMigrationError,
    ExceptionPathTraversalError,
    ExceptionProtocolParsingError,
    ExceptionValidationFrameworkError,
)


class TestExceptionHierarchy:
    """Test the exception inheritance hierarchy."""

    def test_base_exception(self):
        """Test ExceptionValidationFrameworkError is the base exception."""
        exc = ExceptionValidationFrameworkError("Base error")
        assert str(exc) == "Base error"
        assert isinstance(exc, Exception)

    def test_configuration_error_inheritance(self):
        """Test ExceptionConfigurationError inherits from ExceptionValidationFrameworkError."""
        exc = ExceptionConfigurationError("Config error")
        assert isinstance(exc, ExceptionValidationFrameworkError)
        assert isinstance(exc, Exception)
        assert str(exc) == "Config error"

    def test_file_processing_error_inheritance(self):
        """Test ExceptionFileProcessingError inherits from ExceptionValidationFrameworkError."""
        exc = ExceptionFileProcessingError("File error", "/path/to/file.py")
        assert isinstance(exc, ExceptionValidationFrameworkError)
        assert isinstance(exc, Exception)

    def test_protocol_parsing_error_inheritance(self):
        """Test ExceptionProtocolParsingError inherits from ExceptionFileProcessingError."""
        exc = ExceptionProtocolParsingError("Parse error", "/path/to/file.py")
        assert isinstance(exc, ExceptionFileProcessingError)
        assert isinstance(exc, ExceptionValidationFrameworkError)
        assert isinstance(exc, Exception)

    def test_input_validation_error_inheritance(self):
        """Test ExceptionInputValidationError inherits from ExceptionValidationFrameworkError."""
        exc = ExceptionInputValidationError("Invalid input")
        assert isinstance(exc, ExceptionValidationFrameworkError)
        assert isinstance(exc, Exception)

    def test_path_traversal_error_inheritance(self):
        """Test ExceptionPathTraversalError inherits from ExceptionInputValidationError."""
        exc = ExceptionPathTraversalError("Path traversal attempt")
        assert isinstance(exc, ExceptionInputValidationError)
        assert isinstance(exc, ExceptionValidationFrameworkError)
        assert isinstance(exc, Exception)

    def test_audit_error_inheritance(self):
        """Test ExceptionAuditError inherits from ExceptionValidationFrameworkError."""
        exc = ExceptionAuditError("Audit failed")
        assert isinstance(exc, ExceptionValidationFrameworkError)
        assert isinstance(exc, Exception)

    def test_migration_error_inheritance(self):
        """Test ExceptionMigrationError inherits from ExceptionValidationFrameworkError."""
        exc = ExceptionMigrationError("Migration failed")
        assert isinstance(exc, ExceptionValidationFrameworkError)
        assert isinstance(exc, Exception)


class TestExceptionFileProcessing:
    """Test ExceptionFileProcessingError specific functionality."""

    def test_file_processing_error_basic(self):
        """Test basic ExceptionFileProcessingError creation."""
        exc = ExceptionFileProcessingError("Could not read file", "/path/to/file.py")

        assert exc.file_path == "/path/to/file.py"
        assert exc.original_exception is None
        assert str(exc) == "Could not read file [File: /path/to/file.py]"

    def test_file_processing_error_with_original_exception(self):
        """Test ExceptionFileProcessingError with original exception."""
        original = OSError("Permission denied")
        exc = ExceptionFileProcessingError(
            "Could not read file", "/path/to/file.py", original
        )

        assert exc.file_path == "/path/to/file.py"
        assert exc.original_exception is original
        assert str(exc) == "Could not read file [File: /path/to/file.py]"

    def test_file_processing_error_attributes(self):
        """Test ExceptionFileProcessingError attributes are accessible."""
        exc = ExceptionFileProcessingError("Error message", "/test/path.py")

        # Should have file_path attribute
        assert hasattr(exc, "file_path")
        assert exc.file_path == "/test/path.py"

        # Should have original_exception attribute (even if None)
        assert hasattr(exc, "original_exception")
        assert exc.original_exception is None


class TestExceptionProtocolParsingError:
    """Test ExceptionProtocolParsingError specific functionality."""

    def test_protocol_parsing_error_creation(self):
        """Test ExceptionProtocolParsingError creation and inheritance."""
        exc = ExceptionProtocolParsingError(
            "Syntax error in protocol", "/path/to/protocol.py"
        )

        # Should inherit ExceptionFileProcessing behavior
        assert exc.file_path == "/path/to/protocol.py"
        assert str(exc) == "Syntax error in protocol [File: /path/to/protocol.py]"

        # Should be identifiable as specific parsing error
        assert isinstance(exc, ExceptionProtocolParsingError)
        assert isinstance(exc, ExceptionFileProcessingError)

    def test_protocol_parsing_error_with_original(self):
        """Test ExceptionProtocolParsingError with original SyntaxError."""
        syntax_error = SyntaxError("invalid syntax")
        exc = ExceptionProtocolParsingError(
            "Could not parse protocol", "/test.py", syntax_error
        )

        assert exc.original_exception is syntax_error
        assert exc.file_path == "/test.py"


class TestExceptionCatching:
    """Test exception catching patterns."""

    def test_catch_base_exception(self):
        """Test catching all validation exceptions with base class."""
        exceptions_to_test = [
            ExceptionConfigurationError("config"),
            ExceptionFileProcessingError("file", "/path"),
            ExceptionProtocolParsingError("parse", "/path"),
            ExceptionInputValidationError("input"),
            ExceptionPathTraversalError("traversal"),
            ExceptionAuditError("audit"),
            ExceptionMigrationError("migration"),
        ]

        for exc in exceptions_to_test:
            try:
                raise exc
            except ExceptionValidationFrameworkError as caught:
                assert caught is exc
                assert isinstance(caught, ExceptionValidationFrameworkError)
            else:
                pytest.fail(
                    f"Failed to catch {type(exc).__name__} with ExceptionValidationFrameworkError",
                )

    def test_catch_specific_exceptions(self):
        """Test catching specific exception types."""
        # Test ExceptionFileProcessingError catching
        try:
            raise ExceptionProtocolParsingError("parse error", "/path")
        except ExceptionFileProcessingError as exc:
            assert isinstance(exc, ExceptionProtocolParsingError)
            assert exc.file_path == "/path"

        # Test ExceptionInputValidationError catching
        try:
            raise ExceptionPathTraversalError("traversal error")
        except ExceptionInputValidationError as exc:
            assert isinstance(exc, ExceptionPathTraversalError)

    def test_exception_context_preservation(self):
        """Test that exception context is preserved."""
        original_error = ValueError("Original error")

        try:
            try:
                raise original_error
            except ValueError:
                raise ExceptionConfigurationError("Configuration failed")
        except ExceptionConfigurationError as exc:
            # Should be able to access the original exception through __cause__
            assert exc.__cause__ is None  # Not using raise ... from
            # But we can still check the chain
            assert str(exc) == "Configuration failed"


class TestExceptionDocumentation:
    """Test that exceptions have proper documentation."""

    def test_all_exceptions_have_docstrings(self):
        """Test that all exception classes have docstrings."""
        exceptions = [
            ExceptionValidationFrameworkError,
            ExceptionConfigurationError,
            ExceptionFileProcessingError,
            ExceptionProtocolParsingError,
            ExceptionInputValidationError,
            ExceptionPathTraversalError,
            ExceptionAuditError,
            ExceptionMigrationError,
        ]

        for exc_class in exceptions:
            assert exc_class.__doc__ is not None
            assert (
                len(exc_class.__doc__.strip()) > 0
            ), f"{exc_class.__name__} missing docstring"

    def test_exception_docstrings_describe_purpose(self):
        """Test that exception docstrings describe their purpose."""
        # ExceptionConfigurationError should mention configuration
        assert "configuration" in ExceptionConfigurationError.__doc__.lower()

        # ExceptionFileProcessingError should mention file processing
        assert "file" in ExceptionFileProcessingError.__doc__.lower()

        # ExceptionProtocolParsingError should mention parsing
        assert "parsing" in ExceptionProtocolParsingError.__doc__.lower()

        # ExceptionInputValidationError should mention validation
        assert "validation" in ExceptionInputValidationError.__doc__.lower()

        # ExceptionPathTraversalError should mention security/traversal
        doc = ExceptionPathTraversalError.__doc__.lower()
        assert "traversal" in doc or "security" in doc

        # ExceptionAuditError should mention audit
        assert "audit" in ExceptionAuditError.__doc__.lower()

        # ExceptionMigrationError should mention migration
        assert "migration" in ExceptionMigrationError.__doc__.lower()


class TestExceptionUsagePatterns:
    """Test common exception usage patterns."""

    def test_configuration_error_fail_fast(self):
        """Test ExceptionConfigurationError enables fail-fast behavior."""

        # This pattern should be used in ProtocolAuditor.__init__
        def validate_config(path):
            if not path:
                raise ExceptionConfigurationError("Path cannot be empty")
            return True

        with pytest.raises(ExceptionConfigurationError, match="Path cannot be empty"):
            validate_config("")

    def test_file_processing_error_with_context(self):
        """Test ExceptionFileProcessingError provides useful context."""
        file_path = "/important/protocol.py"
        error_msg = "Could not parse AST"

        exc = ExceptionFileProcessingError(error_msg, file_path)

        # Error message should include both the message and file path
        full_msg = str(exc)
        assert error_msg in full_msg
        assert file_path in full_msg
        assert "[File:" in full_msg

    def test_input_validation_error_security(self):
        """Test ExceptionInputValidationError for security validation."""

        def validate_path(path):
            if ".." in path:
                raise ExceptionPathTraversalError(f"Path traversal detected: {path}")
            if not path.startswith("/allowed/"):
                raise ExceptionInputValidationError(
                    f"Path not in allowed directory: {path}"
                )

        with pytest.raises(ExceptionPathTraversalError):
            validate_path("../../etc/passwd")

        with pytest.raises(ExceptionInputValidationError):
            validate_path("/forbidden/path")

        # Valid path should not raise
        try:
            validate_path("/allowed/valid/path")
        except (ExceptionInputValidationError, ExceptionPathTraversalError):
            pytest.fail("Valid path should not raise validation error")

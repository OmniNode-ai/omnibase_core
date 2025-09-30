"""
Tests for validation framework exceptions.

Tests the custom exception hierarchy and error handling behavior.
"""

import pytest

from omnibase_core.validation.exceptions import (
    AuditError,
    ConfigurationError,
    FileProcessingError,
    InputValidationError,
    MigrationError,
    PathTraversalError,
    ProtocolParsingError,
    ValidationFrameworkError,
)


class TestExceptionHierarchy:
    """Test the exception inheritance hierarchy."""

    def test_base_exception(self):
        """Test ValidationFrameworkError is the base exception."""
        exc = ValidationFrameworkError("Base error")
        assert str(exc) == "Base error"
        assert isinstance(exc, Exception)

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inherits from ValidationFrameworkError."""
        exc = ConfigurationError("Config error")
        assert isinstance(exc, ValidationFrameworkError)
        assert isinstance(exc, Exception)
        assert str(exc) == "Config error"

    def test_file_processing_error_inheritance(self):
        """Test FileProcessingError inherits from ValidationFrameworkError."""
        exc = FileProcessingError("File error", "/path/to/file.py")
        assert isinstance(exc, ValidationFrameworkError)
        assert isinstance(exc, Exception)

    def test_protocol_parsing_error_inheritance(self):
        """Test ProtocolParsingError inherits from FileProcessingError."""
        exc = ProtocolParsingError("Parse error", "/path/to/file.py")
        assert isinstance(exc, FileProcessingError)
        assert isinstance(exc, ValidationFrameworkError)
        assert isinstance(exc, Exception)

    def test_input_validation_error_inheritance(self):
        """Test InputValidationError inherits from ValidationFrameworkError."""
        exc = InputValidationError("Invalid input")
        assert isinstance(exc, ValidationFrameworkError)
        assert isinstance(exc, Exception)

    def test_path_traversal_error_inheritance(self):
        """Test PathTraversalError inherits from InputValidationError."""
        exc = PathTraversalError("Path traversal attempt")
        assert isinstance(exc, InputValidationError)
        assert isinstance(exc, ValidationFrameworkError)
        assert isinstance(exc, Exception)

    def test_audit_error_inheritance(self):
        """Test AuditError inherits from ValidationFrameworkError."""
        exc = AuditError("Audit failed")
        assert isinstance(exc, ValidationFrameworkError)
        assert isinstance(exc, Exception)

    def test_migration_error_inheritance(self):
        """Test MigrationError inherits from ValidationFrameworkError."""
        exc = MigrationError("Migration failed")
        assert isinstance(exc, ValidationFrameworkError)
        assert isinstance(exc, Exception)


class TestFileProcessingError:
    """Test FileProcessingError specific functionality."""

    def test_file_processing_error_basic(self):
        """Test basic FileProcessingError creation."""
        exc = FileProcessingError("Could not read file", "/path/to/file.py")

        assert exc.file_path == "/path/to/file.py"
        assert exc.original_exception is None
        assert str(exc) == "Could not read file [File: /path/to/file.py]"

    def test_file_processing_error_with_original_exception(self):
        """Test FileProcessingError with original exception."""
        original = OSError("Permission denied")
        exc = FileProcessingError("Could not read file", "/path/to/file.py", original)

        assert exc.file_path == "/path/to/file.py"
        assert exc.original_exception is original
        assert str(exc) == "Could not read file [File: /path/to/file.py]"

    def test_file_processing_error_attributes(self):
        """Test FileProcessingError attributes are accessible."""
        exc = FileProcessingError("Error message", "/test/path.py")

        # Should have file_path attribute
        assert hasattr(exc, "file_path")
        assert exc.file_path == "/test/path.py"

        # Should have original_exception attribute (even if None)
        assert hasattr(exc, "original_exception")
        assert exc.original_exception is None


class TestProtocolParsingError:
    """Test ProtocolParsingError specific functionality."""

    def test_protocol_parsing_error_creation(self):
        """Test ProtocolParsingError creation and inheritance."""
        exc = ProtocolParsingError("Syntax error in protocol", "/path/to/protocol.py")

        # Should inherit FileProcessingError behavior
        assert exc.file_path == "/path/to/protocol.py"
        assert str(exc) == "Syntax error in protocol [File: /path/to/protocol.py]"

        # Should be identifiable as specific parsing error
        assert isinstance(exc, ProtocolParsingError)
        assert isinstance(exc, FileProcessingError)

    def test_protocol_parsing_error_with_original(self):
        """Test ProtocolParsingError with original SyntaxError."""
        syntax_error = SyntaxError("invalid syntax")
        exc = ProtocolParsingError("Could not parse protocol", "/test.py", syntax_error)

        assert exc.original_exception is syntax_error
        assert exc.file_path == "/test.py"


class TestExceptionCatching:
    """Test exception catching patterns."""

    def test_catch_base_exception(self):
        """Test catching all validation exceptions with base class."""
        exceptions_to_test = [
            ConfigurationError("config"),
            FileProcessingError("file", "/path"),
            ProtocolParsingError("parse", "/path"),
            InputValidationError("input"),
            PathTraversalError("traversal"),
            AuditError("audit"),
            MigrationError("migration"),
        ]

        for exc in exceptions_to_test:
            try:
                raise exc
            except ValidationFrameworkError as caught:
                assert caught is exc
                assert isinstance(caught, ValidationFrameworkError)
            else:
                pytest.fail(
                    f"Failed to catch {type(exc).__name__} with ValidationFrameworkError",
                )

    def test_catch_specific_exceptions(self):
        """Test catching specific exception types."""
        # Test FileProcessingError catching
        try:
            raise ProtocolParsingError("parse error", "/path")
        except FileProcessingError as exc:
            assert isinstance(exc, ProtocolParsingError)
            assert exc.file_path == "/path"

        # Test InputValidationError catching
        try:
            raise PathTraversalError("traversal error")
        except InputValidationError as exc:
            assert isinstance(exc, PathTraversalError)

    def test_exception_context_preservation(self):
        """Test that exception context is preserved."""
        original_error = ValueError("Original error")

        try:
            try:
                raise original_error
            except ValueError:
                raise ConfigurationError("Configuration failed")
        except ConfigurationError as exc:
            # Should be able to access the original exception through __cause__
            assert exc.__cause__ is None  # Not using raise ... from
            # But we can still check the chain
            assert str(exc) == "Configuration failed"


class TestExceptionDocumentation:
    """Test that exceptions have proper documentation."""

    def test_all_exceptions_have_docstrings(self):
        """Test that all exception classes have docstrings."""
        exceptions = [
            ValidationFrameworkError,
            ConfigurationError,
            FileProcessingError,
            ProtocolParsingError,
            InputValidationError,
            PathTraversalError,
            AuditError,
            MigrationError,
        ]

        for exc_class in exceptions:
            assert exc_class.__doc__ is not None
            assert (
                len(exc_class.__doc__.strip()) > 0
            ), f"{exc_class.__name__} missing docstring"

    def test_exception_docstrings_describe_purpose(self):
        """Test that exception docstrings describe their purpose."""
        # ConfigurationError should mention configuration
        assert "configuration" in ConfigurationError.__doc__.lower()

        # FileProcessingError should mention file processing
        assert "file" in FileProcessingError.__doc__.lower()

        # ProtocolParsingError should mention parsing
        assert "parsing" in ProtocolParsingError.__doc__.lower()

        # InputValidationError should mention validation
        assert "validation" in InputValidationError.__doc__.lower()

        # PathTraversalError should mention security/traversal
        doc = PathTraversalError.__doc__.lower()
        assert "traversal" in doc or "security" in doc

        # AuditError should mention audit
        assert "audit" in AuditError.__doc__.lower()

        # MigrationError should mention migration
        assert "migration" in MigrationError.__doc__.lower()


class TestExceptionUsagePatterns:
    """Test common exception usage patterns."""

    def test_configuration_error_fail_fast(self):
        """Test ConfigurationError enables fail-fast behavior."""

        # This pattern should be used in ProtocolAuditor.__init__
        def validate_config(path):
            if not path:
                raise ConfigurationError("Path cannot be empty")
            return True

        with pytest.raises(ConfigurationError, match="Path cannot be empty"):
            validate_config("")

    def test_file_processing_error_with_context(self):
        """Test FileProcessingError provides useful context."""
        file_path = "/important/protocol.py"
        error_msg = "Could not parse AST"

        exc = FileProcessingError(error_msg, file_path)

        # Error message should include both the message and file path
        full_msg = str(exc)
        assert error_msg in full_msg
        assert file_path in full_msg
        assert "[File:" in full_msg

    def test_input_validation_error_security(self):
        """Test InputValidationError for security validation."""

        def validate_path(path):
            if ".." in path:
                raise PathTraversalError(f"Path traversal detected: {path}")
            if not path.startswith("/allowed/"):
                raise InputValidationError(f"Path not in allowed directory: {path}")

        with pytest.raises(PathTraversalError):
            validate_path("../../etc/passwd")

        with pytest.raises(InputValidationError):
            validate_path("/forbidden/path")

        # Valid path should not raise
        try:
            validate_path("/allowed/valid/path")
        except (InputValidationError, PathTraversalError):
            pytest.fail("Valid path should not raise validation error")

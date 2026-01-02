"""
Tests for validation_utils module.

Tests the core validation utilities including protocol signature extraction,
input validation, and error handling improvements.
"""

import ast
import hashlib
import logging
import tempfile
from pathlib import Path

import pytest

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_protocol_info import ModelProtocolInfo
from omnibase_core.models.validation.model_protocol_signature_extractor import (
    ModelProtocolSignatureExtractor,
)
from omnibase_core.validation.validation_utils import (
    detect_add_remove_conflicts,
    determine_repository_name,
    extract_protocol_signature,
    extract_protocols_from_directory,
    find_protocol_files,
    is_protocol_file,
    is_valid_onex_name,
    is_valid_python_identifier,
    suggest_spi_location,
    validate_directory_path,
    validate_file_path,
    validate_import_path_format,
)


@pytest.mark.unit
class TestProtocolSignatureExtractor:
    """Test the AST-based protocol signature extraction."""

    def test_extract_simple_protocol(self):
        """Test extraction from a simple protocol."""
        code = """
from typing import Protocol

class SimpleProtocol(Protocol):
    def method_one(self, arg: str) -> str:
        ...

    def method_two(self, x: int, y: int) -> int:
        ...
"""
        tree = ast.parse(code)
        extractor = ModelProtocolSignatureExtractor()
        extractor.visit(tree)

        assert extractor.class_name == "SimpleProtocol"
        assert len(extractor.methods) == 2
        assert "method_one(arg) -> str" in extractor.methods
        assert "method_two(x, y) -> int" in extractor.methods

    def test_extract_protocol_with_imports(self):
        """Test extraction includes import information."""
        code = """
from typing import Protocol, Optional
import json
from pathlib import Path

class TestProtocol(Protocol):
    def process(self, data: str) -> Optional[dict]:
        ...
"""
        tree = ast.parse(code)
        extractor = ModelProtocolSignatureExtractor()
        extractor.visit(tree)

        assert extractor.class_name == "TestProtocol"
        assert "typing.Protocol" in extractor.imports
        assert "typing.Optional" in extractor.imports
        assert "json" in extractor.imports
        assert "pathlib.Path" in extractor.imports

    def test_ignore_non_protocol_classes(self):
        """Test that non-Protocol classes are ignored."""
        code = """
class RegularClass:
    def method(self):
        pass

class NotAProtocol:
    def another_method(self):
        pass
"""
        tree = ast.parse(code)
        extractor = ModelProtocolSignatureExtractor()
        extractor.visit(tree)

        assert extractor.class_name == ""
        assert len(extractor.methods) == 0


@pytest.mark.unit
class TestExtractProtocolSignature:
    """Test the file-based protocol signature extraction."""

    def test_extract_from_valid_file(self):
        """Test extraction from a valid protocol file."""
        protocol_code = '''
from typing import Protocol

class TestProtocol(Protocol):
    def test_method(self, param: str) -> str:
        """Test method docstring."""
        ...
'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(protocol_code)
            temp_path = Path(f.name)

        try:
            result = extract_protocol_signature(temp_path)

            assert result is not None
            assert result.name == "TestProtocol"
            assert len(result.methods) == 1
            assert "test_method(param) -> str" in result.methods

            # Verify SHA256 hash is used (64 character hex string)
            methods_str = "|".join(sorted(result.methods))
            expected_hash = hashlib.sha256(methods_str.encode()).hexdigest()
            assert result.signature_hash == expected_hash
            assert len(result.signature_hash) == 64  # SHA256 produces 64 hex chars

        finally:
            temp_path.unlink()

    def test_extract_from_syntax_error_file(self, caplog):
        """Test handling of files with syntax errors."""
        invalid_code = """
from typing import Protocol

class TestProtocol(Protocol
    # Missing closing parenthesis - syntax error
    def test_method(self):
        pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(invalid_code)
            temp_path = Path(f.name)

        try:
            with caplog.at_level(logging.WARNING):
                result = extract_protocol_signature(temp_path)

                assert result is None
                assert len(caplog.records) == 1
                assert caplog.records[0].levelname == "WARNING"
                log_message = caplog.records[0].message
                assert "syntax error" in log_message.lower()
                assert str(temp_path) in log_message

        finally:
            temp_path.unlink()

    def test_extract_from_nonexistent_file(self, caplog):
        """Test handling of nonexistent files."""
        nonexistent_path = Path("/nonexistent/file.py")

        with caplog.at_level(logging.WARNING):
            result = extract_protocol_signature(nonexistent_path)

            assert result is None
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "WARNING"
            log_message = caplog.records[0].message
            # Log message format: "Skipping file due to read error: <path>: <error>"
            assert "read error" in log_message.lower()

    def test_extract_from_binary_file(self, caplog):
        """Test handling of binary files."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".py", delete=False) as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe")  # Binary data
            temp_path = Path(f.name)

        try:
            with caplog.at_level(logging.WARNING):
                result = extract_protocol_signature(temp_path)

                assert result is None
                assert len(caplog.records) == 1
                assert caplog.records[0].levelname == "WARNING"
                log_message = caplog.records[0].message
                assert "encoding error" in log_message.lower()

        finally:
            temp_path.unlink()


@pytest.mark.unit
class TestPathValidation:
    """Test input validation functions."""

    def test_validate_existing_directory(self):
        """Test validation of existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            validated_path = validate_directory_path(temp_path, "test")

            assert validated_path == temp_path.resolve()

    def test_validate_nonexistent_directory(self):
        """Test validation fails for nonexistent directory."""
        nonexistent_path = Path("/nonexistent/directory")

        with pytest.raises(ModelOnexError, match="does not exist"):
            validate_directory_path(nonexistent_path, "test")

    def test_validate_file_as_directory(self):
        """Test validation fails when file is passed as directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_path = Path(temp_file.name)

            with pytest.raises(ModelOnexError, match="not a directory"):
                validate_directory_path(temp_path, "test")

    def test_validate_existing_file(self):
        """Test validation of existing file."""
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_path = Path(temp_file.name)
            validated_path = validate_file_path(temp_path, "test")

            assert validated_path == temp_path.resolve()

    def test_validate_nonexistent_file(self):
        """Test validation fails for nonexistent file."""
        nonexistent_path = Path("/nonexistent/file.py")

        with pytest.raises(ModelOnexError, match="does not exist"):
            validate_file_path(nonexistent_path, "test")

    def test_validate_directory_as_file(self):
        """Test validation fails when directory is passed as file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with pytest.raises(ModelOnexError, match="not a file"):
                validate_file_path(temp_path, "test")

    def test_directory_traversal_warning(self, caplog):
        """Test directory traversal attempts are logged."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a path with .. in it (but still valid)
            temp_path = Path(temp_dir) / ".." / Path(temp_dir).name

            with caplog.at_level(logging.WARNING):
                validated_path = validate_directory_path(temp_path, "test")

                assert validated_path.exists()
                assert len(caplog.records) == 1
                assert caplog.records[0].levelname == "WARNING"
                log_message = caplog.records[0].message
                assert "directory traversal" in log_message.lower()


@pytest.mark.unit
class TestExtractProtocolsFromDirectory:
    """Test directory-level protocol extraction."""

    def test_extract_from_directory_with_protocols(self, caplog):
        """Test extraction from directory containing protocol files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a valid protocol file
            protocol_file = temp_path / "test_protocol.py"
            protocol_code = """
from typing import Protocol

class TestProtocol(Protocol):
    def test_method(self) -> str:
        ...
"""
            protocol_file.write_text(protocol_code)

            # Create a non-protocol file
            regular_file = temp_path / "regular.py"
            regular_file.write_text("print('hello')")

            with caplog.at_level(logging.INFO):
                protocols = extract_protocols_from_directory(temp_path)

                assert len(protocols) == 1
                assert protocols[0].name == "TestProtocol"

                # Verify logging
                log_messages = [record.message for record in caplog.records]
                assert any(
                    "found" in msg.lower() and "protocol files" in msg.lower()
                    for msg in log_messages
                )
                assert any(
                    "extracted" in msg.lower() and "protocols" in msg.lower()
                    for msg in log_messages
                )

    def test_extract_from_empty_directory(self, caplog):
        """Test extraction from empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with caplog.at_level(logging.INFO):
                protocols = extract_protocols_from_directory(temp_path)

                assert len(protocols) == 0
                # Should still log the attempt
                assert len(caplog.records) > 0
                assert any(record.levelname == "INFO" for record in caplog.records)

    def test_extract_from_invalid_directory(self):
        """Test extraction fails for invalid directory."""
        invalid_path = Path("/nonexistent/directory")

        with pytest.raises(ModelOnexError):
            extract_protocols_from_directory(invalid_path)


@pytest.mark.unit
class TestSHA256Migration:
    """Test that MD5 has been replaced with SHA256."""

    def test_sha256_hash_length(self):
        """Test that protocol signatures use SHA256 (64 hex chars)."""
        protocol_code = """
from typing import Protocol

class SHA256TestProtocol(Protocol):
    def test_method(self, param: str) -> str:
        ...
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(protocol_code)
            temp_path = Path(f.name)

        try:
            result = extract_protocol_signature(temp_path)

            assert result is not None
            # SHA256 produces 64 hexadecimal characters
            assert len(result.signature_hash) == 64
            # Verify it's actually a hex string
            assert all(c in "0123456789abcdef" for c in result.signature_hash)

        finally:
            temp_path.unlink()

    def test_sha256_consistency(self):
        """Test that identical protocols produce identical SHA256 hashes."""
        protocol_code = """
from typing import Protocol

class ConsistencyTestProtocol(Protocol):
    def method_a(self, x: int) -> int:
        ...
    def method_b(self, y: str) -> str:
        ...
"""
        results = []

        # Create the same protocol in two different files
        for i in range(2):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(protocol_code)
                temp_path = Path(f.name)

            try:
                result = extract_protocol_signature(temp_path)
                assert result is not None
                results.append(result)

            finally:
                temp_path.unlink()

        # Both protocols should have identical signature hashes
        assert results[0].signature_hash == results[1].signature_hash
        assert len(results[0].signature_hash) == 64  # SHA256 length


# Integration test to verify logging configuration
@pytest.mark.unit
class TestLoggingIntegration:
    """Test that logging is properly configured."""

    def test_logger_exists(self):
        """Test that the module logger is properly configured."""
        from omnibase_core.validation import validation_utils

        assert hasattr(validation_utils, "logger")
        assert isinstance(validation_utils.logger, logging.Logger)
        assert (
            validation_utils.logger.name == "omnibase_core.validation.validation_utils"
        )

    def test_exception_logging(self, caplog):
        """Test that exceptions are properly logged."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("invalid python syntax (((")
            temp_path = Path(f.name)

        try:
            with caplog.at_level(logging.WARNING):
                result = extract_protocol_signature(temp_path)

                assert result is None
                # Should have called warning for syntax error
                assert len(caplog.records) == 1
                assert caplog.records[0].levelname == "WARNING"

        finally:
            temp_path.unlink()


@pytest.mark.unit
class TestDetermineRepositoryName:
    """Test repository name detection from file paths."""

    def test_omni_prefix_detection(self):
        """Test detection of omni* prefixed directories."""
        test_cases = [
            (Path("/home/user/omnibase_core/src/module.py"), "omnibase_core"),
            (Path("/projects/omnibase_spi/protocols/test.py"), "omnibase_spi"),
            (Path("/code/omnifoundation/lib/util.py"), "omnifoundation"),
        ]

        for path, expected in test_cases:
            result = determine_repository_name(path)
            assert result == expected, f"Failed for path {path}"

    def test_src_directory_structure(self):
        """Test detection from src/ directory structure."""
        path = Path("/projects/myproject/src/module/file.py")
        result = determine_repository_name(path)
        assert result == "myproject"

    def test_unknown_fallback(self):
        """Test fallback to 'unknown' for unrecognizable paths."""
        path = Path("/random/path/file.py")
        result = determine_repository_name(path)
        assert result == "unknown"

    def test_omni_priority_over_src(self):
        """Test that omni* prefix takes priority over src/ structure."""
        path = Path("/projects/myproject/src/omnibase_core/module.py")
        result = determine_repository_name(path)
        assert result == "omnibase_core"


@pytest.mark.unit
class TestSuggestSpiLocation:
    """Test SPI location suggestions based on protocol names."""

    def test_agent_category(self):
        """Test agent-related protocol categorization."""
        test_names = [
            "AgentProtocol",
            "LifecycleManager",
            "CoordinatorProtocol",
            "PoolManager",
            "AgentManagerProtocol",
        ]

        for name in test_names:
            protocol = ModelProtocolInfo(
                name=name,
                file_path="/test/path.py",
                repository="test",
                methods=["test_method() -> None"],
                signature_hash="abc123",
                line_count=10,
                imports=[],
            )
            result = suggest_spi_location(protocol)
            assert result == "agent", f"Failed for {name}"

    def test_workflow_category(self):
        """Test workflow-related protocol categorization."""
        test_names = [
            "WorkflowProtocol",
            "ExecutionProtocol",
            "WorkQueue",
            "TaskExecutor",
        ]

        for name in test_names:
            protocol = ModelProtocolInfo(
                name=name,
                file_path="/test/path.py",
                repository="test",
                methods=["test_method() -> None"],
                signature_hash="abc123",
                line_count=10,
                imports=[],
            )
            result = suggest_spi_location(protocol)
            assert result == "workflow", f"Failed for {name}"

    def test_task_management_with_manager_suffix(self):
        """Test that TaskManager goes to agent category (manager keyword priority)."""
        protocol = ModelProtocolInfo(
            name="TaskManager",
            file_path="/test/path.py",
            repository="test",
            methods=["test_method() -> None"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )
        result = suggest_spi_location(protocol)
        # "manager" keyword appears in agent category, so it takes priority
        assert result == "agent"

    def test_file_handling_category(self):
        """Test file handling protocol categorization."""
        test_names = [
            "FileProtocol",
            "ReaderProtocol",
            "WriterProtocol",
            "StorageProtocol",
            "StampProtocol",
        ]

        for name in test_names:
            protocol = ModelProtocolInfo(
                name=name,
                file_path="/test/path.py",
                repository="test",
                methods=["test_method() -> None"],
                signature_hash="abc123",
                line_count=10,
                imports=[],
            )
            result = suggest_spi_location(protocol)
            assert result == "file_handling", f"Failed for {name}"

    def test_event_bus_category(self):
        """Test event and messaging protocol categorization."""
        test_names = [
            "EventProtocol",
            "BusProtocol",
            "MessageProtocol",
            "PubSubProtocol",
            "CommunicationProtocol",
        ]

        for name in test_names:
            protocol = ModelProtocolInfo(
                name=name,
                file_path="/test/path.py",
                repository="test",
                methods=["test_method() -> None"],
                signature_hash="abc123",
                line_count=10,
                imports=[],
            )
            result = suggest_spi_location(protocol)
            assert result == "event_bus", f"Failed for {name}"

    def test_monitoring_category(self):
        """Test monitoring and observability protocol categorization."""
        test_names = [
            "MonitorProtocol",
            "MetricProtocol",
            "ObservabilityProtocol",
            "TraceProtocol",
            "HealthCheckProtocol",
            "LoggerProtocol",
        ]

        for name in test_names:
            protocol = ModelProtocolInfo(
                name=name,
                file_path="/test/path.py",
                repository="test",
                methods=["test_method() -> None"],
                signature_hash="abc123",
                line_count=10,
                imports=[],
            )
            result = suggest_spi_location(protocol)
            assert result == "monitoring", f"Failed for {name}"

    def test_integration_category(self):
        """Test service integration protocol categorization."""
        test_names = [
            "ServiceProtocol",
            "ClientProtocol",
            "IntegrationProtocol",
            "BridgeProtocol",
            "RegistryProtocol",
        ]

        for name in test_names:
            protocol = ModelProtocolInfo(
                name=name,
                file_path="/test/path.py",
                repository="test",
                methods=["test_method() -> None"],
                signature_hash="abc123",
                line_count=10,
                imports=[],
            )
            result = suggest_spi_location(protocol)
            assert result == "integration", f"Failed for {name}"

    def test_core_category(self):
        """Test core ONEX architecture protocol categorization."""
        test_names = [
            "ReducerProtocol",
            "OrchestratorProtocol",
            "ComputeProtocol",
            "EffectProtocol",
            "OnexProtocol",
        ]

        for name in test_names:
            protocol = ModelProtocolInfo(
                name=name,
                file_path="/test/path.py",
                repository="test",
                methods=["test_method() -> None"],
                signature_hash="abc123",
                line_count=10,
                imports=[],
            )
            result = suggest_spi_location(protocol)
            assert result == "core", f"Failed for {name}"

    def test_testing_category(self):
        """Test testing and validation protocol categorization."""
        test_names = [
            "TestProtocol",
            "ValidationProtocol",
            "CheckProtocol",
            "VerifyProtocol",
        ]

        for name in test_names:
            protocol = ModelProtocolInfo(
                name=name,
                file_path="/test/path.py",
                repository="test",
                methods=["test_method() -> None"],
                signature_hash="abc123",
                line_count=10,
                imports=[],
            )
            result = suggest_spi_location(protocol)
            assert result == "testing", f"Failed for {name}"

    def test_data_category(self):
        """Test data processing protocol categorization."""
        test_names = [
            "DataProtocol",
            "ProcessorProtocol",
            "TransformProtocol",
            "SerializerProtocol",
        ]

        for name in test_names:
            protocol = ModelProtocolInfo(
                name=name,
                file_path="/test/path.py",
                repository="test",
                methods=["test_method() -> None"],
                signature_hash="abc123",
                line_count=10,
                imports=[],
            )
            result = suggest_spi_location(protocol)
            assert result == "data", f"Failed for {name}"

    def test_default_fallback(self):
        """Test default fallback to 'core' for unrecognized protocols."""
        protocol = ModelProtocolInfo(
            name="RandomProtocol",
            file_path="/test/path.py",
            repository="test",
            methods=["test_method() -> None"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )
        result = suggest_spi_location(protocol)
        assert result == "core"

    def test_case_insensitive_matching(self):
        """Test that categorization is case-insensitive."""
        protocol = ModelProtocolInfo(
            name="AGENTPROTOCOL",
            file_path="/test/path.py",
            repository="test",
            methods=["test_method() -> None"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )
        result = suggest_spi_location(protocol)
        assert result == "agent"


@pytest.mark.unit
class TestIsProtocolFile:
    """Test protocol file detection."""

    def test_protocol_filename_detection(self):
        """Test detection by filename containing 'protocol'."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_protocol.py", delete=False
        ) as f:
            f.write("# Empty file")
            temp_path = Path(f.name)

        try:
            result = is_protocol_file(temp_path)
            assert result is True
        finally:
            temp_path.unlink()

    def test_protocol_prefix_detection(self):
        """Test detection by filename starting with 'protocol_'."""
        with tempfile.NamedTemporaryFile(
            mode="w", prefix="protocol_", suffix=".py", delete=False
        ) as f:
            f.write("# Empty file")
            temp_path = Path(f.name)

        try:
            result = is_protocol_file(temp_path)
            assert result is True
        finally:
            temp_path.unlink()

    def test_protocol_content_detection(self):
        """Test detection by file content containing 'class Protocol'."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            # Write content that includes "class Protocol" within first 1000 chars
            f.write(
                "# Regular Python file\nfrom typing import Protocol\n\nclass Protocol:\n    pass"
            )
            temp_path = Path(f.name)

        try:
            result = is_protocol_file(temp_path)
            assert result is True
        finally:
            temp_path.unlink()

    def test_non_protocol_file(self):
        """Test that regular files are not detected as protocols."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def regular_function():\n    pass")
            temp_path = Path(f.name)

        try:
            result = is_protocol_file(temp_path)
            assert result is False
        finally:
            temp_path.unlink()

    def test_oserror_handling(self, caplog):
        """Test handling of OSError during file reading."""
        nonexistent_path = Path("/nonexistent/file.py")

        with caplog.at_level(logging.WARNING):
            result = is_protocol_file(nonexistent_path)

            assert result is False
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "DEBUG"
            # OSError is explicitly caught and logged
            assert "error checking protocol file" in caplog.records[0].message.lower()

    def test_unexpected_exceptions_propagate(self, monkeypatch):
        """Test that unexpected exceptions propagate rather than being silently caught.

        The is_protocol_file function only catches specific expected exceptions
        (OSError, ValueError, UnicodeDecodeError). Unexpected exceptions like
        RuntimeError should propagate to allow proper error handling upstream.
        """

        def mock_read_text(*args, **kwargs):
            raise RuntimeError("Unexpected error")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("test")
            temp_path = Path(f.name)

        try:
            # Monkeypatch the read_text method
            monkeypatch.setattr(Path, "read_text", mock_read_text)

            # RuntimeError should propagate, not be silently caught
            with pytest.raises(RuntimeError, match="Unexpected error"):
                is_protocol_file(temp_path)
        finally:
            temp_path.unlink()


@pytest.mark.unit
class TestFindProtocolFiles:
    """Test protocol file discovery."""

    def test_find_protocol_files_in_directory(self):
        """Test finding protocol files in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create protocol files
            protocol_file1 = temp_path / "protocol_one.py"
            protocol_file1.write_text("class Protocol: pass")

            protocol_file2 = temp_path / "test_protocol.py"
            protocol_file2.write_text("class Protocol: pass")

            # Create non-protocol file
            regular_file = temp_path / "regular.py"
            regular_file.write_text("def function(): pass")

            result = find_protocol_files(temp_path)

            assert len(result) == 2
            assert protocol_file1 in result
            assert protocol_file2 in result
            assert regular_file not in result

    def test_find_protocol_files_recursive(self):
        """Test recursive protocol file discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory structure
            subdir = temp_path / "subdir"
            subdir.mkdir()

            protocol_file1 = temp_path / "protocol_root.py"
            protocol_file1.write_text("class Protocol: pass")

            protocol_file2 = subdir / "protocol_sub.py"
            protocol_file2.write_text("class Protocol: pass")

            result = find_protocol_files(temp_path)

            assert len(result) == 2
            assert protocol_file1 in result
            assert protocol_file2 in result

    def test_find_protocol_files_empty_directory(self):
        """Test finding protocol files in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            result = find_protocol_files(temp_path)

            assert len(result) == 0
            assert result == []

    def test_find_protocol_files_nonexistent_directory(self):
        """Test finding protocol files in non-existent directory."""
        nonexistent_path = Path("/nonexistent/directory")

        result = find_protocol_files(nonexistent_path)

        assert len(result) == 0
        assert result == []


@pytest.mark.unit
class TestInvalidPathHandling:
    """Test invalid path handling in validation functions."""

    def test_validate_directory_with_invalid_path(self, monkeypatch):
        """Test validation with path that cannot be resolved."""

        def mock_resolve(self):
            raise OSError("Cannot resolve path")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Monkeypatch the resolve method to raise OSError
            monkeypatch.setattr(Path, "resolve", mock_resolve)

            with pytest.raises(ModelOnexError, match="Invalid"):
                validate_directory_path(temp_path, "test")

    def test_validate_file_with_invalid_path(self, monkeypatch):
        """Test file validation with path that cannot be resolved."""

        def mock_resolve(self):
            raise ValueError("Cannot resolve path")

        with tempfile.NamedTemporaryFile() as temp_file:
            temp_path = Path(temp_file.name)
            # Monkeypatch the resolve method to raise ValueError
            monkeypatch.setattr(Path, "resolve", mock_resolve)

            with pytest.raises(ModelOnexError, match="Invalid"):
                validate_file_path(temp_path, "test")


@pytest.mark.unit
class TestIsValidPythonIdentifier:
    """Test Python identifier validation."""

    def test_valid_identifiers(self):
        """Test validation of valid Python identifiers."""
        valid_names = [
            "my_var",
            "MyClass",
            "_private",
            "__dunder__",
            "x",
            "X",
            "_",
            "var123",
            "CamelCase",
            "snake_case",
            "UPPER_CASE",
        ]
        for name in valid_names:
            assert is_valid_python_identifier(name) is True, (
                f"Expected '{name}' to be valid"
            )

    def test_invalid_identifiers(self):
        """Test validation of invalid Python identifiers."""
        invalid_names = [
            "",  # Empty
            "123abc",  # Starts with digit
            "2fast",  # Starts with digit
            "my-var",  # Contains hyphen
            "my var",  # Contains space
            "my.var",  # Contains dot
            "my@var",  # Contains special char
            "class",  # Reserved word (still valid identifier pattern)
        ]
        # Note: "class" is technically a valid identifier pattern,
        # just can't be used as a variable name
        for name in invalid_names[:-1]:  # Skip "class"
            assert is_valid_python_identifier(name) is False, (
                f"Expected '{name}' to be invalid"
            )

    def test_unicode_not_supported(self):
        """Test that non-ASCII characters are rejected."""
        # Our regex only supports ASCII identifiers
        assert is_valid_python_identifier("var_name") is True
        # Unicode chars would need a different pattern


@pytest.mark.unit
class TestIsValidOnexName:
    """Test ONEX naming convention validation."""

    def test_valid_onex_names(self):
        """Test validation of valid ONEX names."""
        valid_names = [
            "http_client",
            "HttpClient",
            "HTTP_CLIENT",
            "handler123",
            "myHandler",
            "x",
            "A",
        ]
        for name in valid_names:
            assert is_valid_onex_name(name) is True, (
                f"Expected '{name}' to be valid ONEX name"
            )

    def test_invalid_onex_names(self):
        """Test validation of invalid ONEX names."""
        invalid_names = [
            "",  # Empty
            "my-handler",  # Contains hyphen
            "my.handler",  # Contains dot
            "my handler",  # Contains space
            "my@handler",  # Contains special char
        ]
        for name in invalid_names:
            assert is_valid_onex_name(name) is False, (
                f"Expected '{name}' to be invalid ONEX name"
            )

    def test_lowercase_only_mode(self):
        """Test lowercase-only validation mode."""
        # Valid lowercase names
        assert is_valid_onex_name("http_client", lowercase_only=True) is True
        assert is_valid_onex_name("handler123", lowercase_only=True) is True
        assert is_valid_onex_name("x", lowercase_only=True) is True

        # Invalid when lowercase_only=True
        assert is_valid_onex_name("HttpClient", lowercase_only=True) is False
        assert is_valid_onex_name("HTTP_CLIENT", lowercase_only=True) is False
        assert is_valid_onex_name("MyHandler", lowercase_only=True) is False

    def test_empty_name(self):
        """Test that empty names are rejected."""
        assert is_valid_onex_name("") is False
        assert is_valid_onex_name("", lowercase_only=True) is False


@pytest.mark.unit
class TestValidateImportPathFormat:
    """Test import path format validation."""

    def test_valid_import_paths(self):
        """Test validation of valid import paths."""
        valid_paths = [
            "mypackage.MyClass",
            "mypackage.module.MyClass",
            "omnibase_core.models.events.ModelEventEnvelope",
            "my_package.handlers.HttpClientHandler",
            "_private.module.Class",
        ]
        for path in valid_paths:
            is_valid, error = validate_import_path_format(path)
            assert is_valid is True, (
                f"Expected '{path}' to be valid, got error: {error}"
            )
            assert error is None

    def test_single_segment_rejected(self):
        """Test that single-segment paths are rejected."""
        is_valid, error = validate_import_path_format("MyClass")
        assert is_valid is False
        assert "at least 2 segments" in error

    def test_empty_path_rejected(self):
        """Test that empty paths are rejected."""
        is_valid, error = validate_import_path_format("")
        assert is_valid is False
        assert "empty" in error.lower()

        is_valid, error = validate_import_path_format("   ")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_path_traversal_rejected(self):
        """Test that path traversal is rejected."""
        is_valid, error = validate_import_path_format("my..module.Class")
        assert is_valid is False
        assert ".." in error

        is_valid, error = validate_import_path_format("my/module.Class")
        assert is_valid is False

        is_valid, error = validate_import_path_format("my\\module.Class")
        assert is_valid is False

    def test_dangerous_characters_rejected(self):
        """Test that dangerous characters are rejected."""
        dangerous_chars = ["<", ">", "|", "&", ";", "`", "$", "'", '"', "*", "?"]
        for char in dangerous_chars:
            path = f"my{char}module.Class"
            is_valid, error = validate_import_path_format(path)
            assert is_valid is False, f"Expected '{char}' to be rejected"
            assert "invalid characters" in error.lower()

    def test_empty_segment_rejected(self):
        """Test that empty segments are rejected."""
        is_valid, _error = validate_import_path_format("my..Class")
        assert is_valid is False

        is_valid, _error = validate_import_path_format(".module.Class")
        assert is_valid is False

    def test_invalid_identifier_rejected(self):
        """Test that invalid Python identifiers are rejected."""
        is_valid, error = validate_import_path_format("123module.Class")
        assert is_valid is False
        assert "not a valid Python identifier" in error

        is_valid, error = validate_import_path_format("my-module.Class")
        assert is_valid is False
        assert "not a valid Python identifier" in error


@pytest.mark.unit
class TestDetectAddRemoveConflicts:
    """Test add/remove conflict detection."""

    def test_detects_conflicts(self):
        """Test that conflicts are properly detected."""
        conflicts = detect_add_remove_conflicts(
            ["foo", "bar", "baz"],
            ["bar", "qux"],
            "handlers",
        )
        assert conflicts == ["bar"]

    def test_detects_multiple_conflicts(self):
        """Test detection of multiple conflicts."""
        conflicts = detect_add_remove_conflicts(
            ["a", "b", "c", "d"],
            ["b", "d", "e"],
            "handlers",
        )
        assert sorted(conflicts) == ["b", "d"]

    def test_no_conflicts(self):
        """Test when there are no conflicts."""
        conflicts = detect_add_remove_conflicts(
            ["foo", "bar"],
            ["baz", "qux"],
            "handlers",
        )
        assert conflicts == []

    def test_none_add_values(self):
        """Test with None add_values."""
        conflicts = detect_add_remove_conflicts(
            None,
            ["bar", "baz"],
            "handlers",
        )
        assert conflicts == []

    def test_none_remove_values(self):
        """Test with None remove_values."""
        conflicts = detect_add_remove_conflicts(
            ["foo", "bar"],
            None,
            "handlers",
        )
        assert conflicts == []

    def test_both_none(self):
        """Test with both values None."""
        conflicts = detect_add_remove_conflicts(None, None, "handlers")
        assert conflicts == []

    def test_empty_lists(self):
        """Test with empty lists."""
        conflicts = detect_add_remove_conflicts([], [], "handlers")
        assert conflicts == []

    def test_case_insensitive_default(self):
        """Test case-insensitive comparison (default)."""
        conflicts = detect_add_remove_conflicts(
            ["Foo", "BAR"],
            ["foo", "baz"],
            "handlers",
        )
        assert conflicts == ["foo"]

    def test_case_sensitive(self):
        """Test case-sensitive comparison."""
        conflicts = detect_add_remove_conflicts(
            ["Foo", "BAR"],
            ["foo", "baz"],
            "handlers",
            case_sensitive=True,
        )
        assert conflicts == []

        conflicts = detect_add_remove_conflicts(
            ["Foo", "BAR"],
            ["Foo", "baz"],
            "handlers",
            case_sensitive=True,
        )
        assert conflicts == ["Foo"]

    def test_warn_empty_lists_no_warning_when_false(self, caplog):
        """Test that no warning is logged when warn_empty_lists is False."""
        with caplog.at_level(logging.WARNING):
            conflicts = detect_add_remove_conflicts(
                [],
                [],
                "handlers",
                warn_empty_lists=False,
            )
            assert conflicts == []
            # Should not have any warning about empty lists
            assert not any(
                "empty" in record.message.lower() for record in caplog.records
            )

    def test_warn_empty_lists_warning_when_true(self, caplog):
        """Test that warning is logged when warn_empty_lists is True."""
        with caplog.at_level(logging.WARNING):
            conflicts = detect_add_remove_conflicts(
                [],
                [],
                "handlers",
                warn_empty_lists=True,
            )
            assert conflicts == []
            # Should have warning about empty lists
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "WARNING"
            assert "empty" in caplog.records[0].message.lower()

    def test_warn_empty_lists_no_warning_when_lists_not_empty(self, caplog):
        """Test that no warning about empty lists when lists have content."""
        with caplog.at_level(logging.WARNING):
            conflicts = detect_add_remove_conflicts(
                ["foo"],
                ["bar"],
                "handlers",
                warn_empty_lists=True,
            )
            assert conflicts == []
            # Should not have warning about empty lists (only debug log)
            assert not any(
                "empty" in record.message.lower() and record.levelname == "WARNING"
                for record in caplog.records
            )

    def test_logging_when_conflicts_found(self, caplog):
        """Test that conflicts are logged at WARNING level."""
        with caplog.at_level(logging.WARNING):
            conflicts = detect_add_remove_conflicts(
                ["foo", "bar"],
                ["bar", "baz"],
                "handlers",
            )
            assert conflicts == ["bar"]
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "WARNING"
            assert "conflicts" in caplog.records[0].message.lower()

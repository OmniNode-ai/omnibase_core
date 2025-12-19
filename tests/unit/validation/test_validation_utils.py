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

from omnibase_core.errors.exceptions import ExceptionInputValidationError
from omnibase_core.models.validation.model_protocol_info import ModelProtocolInfo
from omnibase_core.models.validation.model_protocol_signature_extractor import (
    ModelProtocolSignatureExtractor,
)
from omnibase_core.validation.validation_utils import (
    determine_repository_name,
    extract_protocol_signature,
    extract_protocols_from_directory,
    find_protocol_files,
    is_protocol_file,
    suggest_spi_location,
    validate_directory_path,
    validate_file_path,
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

        with caplog.at_level(logging.ERROR):
            result = extract_protocol_signature(nonexistent_path)

            assert result is None
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "ERROR"
            log_message = caplog.records[0].message
            assert "error reading file" in log_message.lower()

    def test_extract_from_binary_file(self, caplog):
        """Test handling of binary files."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".py", delete=False) as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe")  # Binary data
            temp_path = Path(f.name)

        try:
            with caplog.at_level(logging.ERROR):
                result = extract_protocol_signature(temp_path)

                assert result is None
                assert len(caplog.records) == 1
                assert caplog.records[0].levelname == "ERROR"
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

        with pytest.raises(ExceptionInputValidationError, match="does not exist"):
            validate_directory_path(nonexistent_path, "test")

    def test_validate_file_as_directory(self):
        """Test validation fails when file is passed as directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_path = Path(temp_file.name)

            with pytest.raises(ExceptionInputValidationError, match="not a directory"):
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

        with pytest.raises(ExceptionInputValidationError, match="does not exist"):
            validate_file_path(nonexistent_path, "test")

    def test_validate_directory_as_file(self):
        """Test validation fails when directory is passed as file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with pytest.raises(ExceptionInputValidationError, match="not a file"):
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

        with pytest.raises(ExceptionInputValidationError):
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

        with caplog.at_level(logging.DEBUG):
            result = is_protocol_file(nonexistent_path)

            assert result is False
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "DEBUG"
            assert "could not read file" in caplog.records[0].message.lower()

    def test_generic_exception_handling(self, caplog, monkeypatch):
        """Test handling of unexpected exceptions."""

        def mock_read_text(*args, **kwargs):
            raise RuntimeError("Unexpected error")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("test")
            temp_path = Path(f.name)

        try:
            # Monkeypatch the read_text method
            monkeypatch.setattr(Path, "read_text", mock_read_text)

            with caplog.at_level(logging.DEBUG):
                result = is_protocol_file(temp_path)

                assert result is False
                assert len(caplog.records) == 1
                assert caplog.records[0].levelname == "DEBUG"
                assert "unexpected error" in caplog.records[0].message.lower()
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

            with pytest.raises(ExceptionInputValidationError, match="Invalid"):
                validate_directory_path(temp_path, "test")

    def test_validate_file_with_invalid_path(self, monkeypatch):
        """Test file validation with path that cannot be resolved."""

        def mock_resolve(self):
            raise ValueError("Cannot resolve path")

        with tempfile.NamedTemporaryFile() as temp_file:
            temp_path = Path(temp_file.name)
            # Monkeypatch the resolve method to raise ValueError
            monkeypatch.setattr(Path, "resolve", mock_resolve)

            with pytest.raises(ExceptionInputValidationError, match="Invalid"):
                validate_file_path(temp_path, "test")

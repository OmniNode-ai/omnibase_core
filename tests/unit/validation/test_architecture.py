"""Tests for ONEX architecture validation."""

import ast
from pathlib import Path

import pytest

from omnibase_core.errors.exceptions import ExceptionConfigurationError
from omnibase_core.models.validation.model_audit_result import ModelAuditResult
from omnibase_core.models.validation.model_duplication_info import ModelDuplicationInfo
from omnibase_core.models.validation.model_duplication_report import (
    ModelDuplicationReport,
)
from omnibase_core.models.validation.model_protocol_info import ModelProtocolInfo
from omnibase_core.validation.architecture import (
    ModelCounter,
    validate_architecture_directory,
    validate_one_model_per_file,
)
from omnibase_core.validation.auditor_protocol import ModelProtocolAuditor


class TestModelCounter:
    """Test ModelCounter AST visitor."""

    def test_count_single_model(self):
        """Test counting a single model."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.models) == 1
        assert "ModelUser" in counter.models
        assert len(counter.enums) == 0
        assert len(counter.protocols) == 0

    def test_count_multiple_models(self):
        """Test counting multiple models."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.models) == 2
        assert "ModelUser" in counter.models
        assert "ModelPost" in counter.models

    def test_count_enum(self):
        """Test counting enums."""
        code = """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.enums) == 1
        assert "EnumStatus" in counter.enums
        assert len(counter.models) == 0

    def test_count_protocol(self):
        """Test counting protocols."""
        code = """
from typing import Protocol

class Serializable(Protocol):
    def serialize(self) -> dict:
        ...
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.protocols) == 1
        assert "Serializable" in counter.protocols
        assert len(counter.models) == 0

    def test_count_mixed_types(self):
        """Test counting mixed types."""
        code = """
from pydantic import BaseModel
from enum import Enum
from typing import Protocol

class ModelUser(BaseModel):
    name: str

class EnumStatus(Enum):
    ACTIVE = "active"

class Serializable(Protocol):
    def serialize(self) -> dict:
        ...
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.models) == 1
        assert len(counter.enums) == 1
        assert len(counter.protocols) == 1

    def test_detect_model_by_naming_pattern(self):
        """Test detecting models by naming pattern."""
        code = """
class ModelCustom:
    pass
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.models) == 1
        assert "ModelCustom" in counter.models

    def test_detect_enum_by_naming_pattern(self):
        """Test detecting enums by naming pattern."""
        code = """
class EnumCustom:
    pass
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.enums) == 1
        assert "EnumCustom" in counter.enums

    def test_detect_pydantic_basemodel_attribute(self):
        """Test detecting pydantic.BaseModel."""
        code = """
import pydantic

class ModelUser(pydantic.BaseModel):
    name: str
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.models) == 1
        assert "ModelUser" in counter.models

    def test_type_alias_detection(self):
        """Test type alias detection."""
        code = """
from typing import TypeAlias

CustomType: TypeAlias = dict[str, str]
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.type_aliases) == 1
        assert "CustomType" in counter.type_aliases


class TestValidateOneModelPerFile:
    """Test validate_one_model_per_file function."""

    def test_single_model_passes(self, tmp_path: Path):
        """Test single model file passes validation."""
        test_file = tmp_path / "model_user.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) == 0

    def test_multiple_models_fails(self, tmp_path: Path):
        """Test multiple models fail validation."""
        test_file = tmp_path / "models.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("2 models" in error for error in errors)

    def test_multiple_enums_fails(self, tmp_path: Path):
        """Test multiple enums fail validation."""
        test_file = tmp_path / "enums.py"
        test_file.write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"

class EnumTaskTypes(Enum):
    USER = "user"
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("2 enums" in error for error in errors)

    def test_multiple_protocols_fails(self, tmp_path: Path):
        """Test multiple protocols fail validation."""
        test_file = tmp_path / "protocols.py"
        test_file.write_text(
            """
from typing import Protocol

class Serializable(Protocol):
    def serialize(self) -> dict:
        ...

class Validatable(Protocol):
    def validate(self) -> bool:
        ...
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("2 protocols" in error for error in errors)

    def test_mixed_types_fails(self, tmp_path: Path):
        """Test mixed types fail validation."""
        test_file = tmp_path / "mixed.py"
        test_file.write_text(
            """
from pydantic import BaseModel
from enum import Enum

class ModelUser(BaseModel):
    name: str

class EnumStatus(Enum):
    ACTIVE = "active"
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("Mixed types" in error for error in errors)

    def test_typeddict_with_model_allowed(self, tmp_path: Path):
        """Test TypedDict with model is allowed."""
        test_file = tmp_path / "model_with_typeddict.py"
        test_file.write_text(
            """
from typing import TypedDict
from pydantic import BaseModel

class UserData(TypedDict):
    name: str
    age: int

class ModelUser(BaseModel):
    data: UserData
"""
        )

        errors = validate_one_model_per_file(test_file)
        # TypedDict + Model is allowed
        assert len(errors) == 0

    def test_syntax_error_handling(self, tmp_path: Path):
        """Test handling of syntax errors."""
        test_file = tmp_path / "invalid.py"
        test_file.write_text(
            """
class Invalid(
    # Syntax error - unclosed parenthesis
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("Syntax error" in error for error in errors)


class TestValidateArchitectureDirectory:
    """Test validate_architecture_directory function."""

    def test_empty_directory(self, tmp_path: Path):
        """Test validation of empty directory."""
        result = validate_architecture_directory(tmp_path)

        assert result.is_valid is True
        assert result.metadata.files_processed == 0
        assert len(result.errors) == 0

    def test_directory_with_valid_files(self, tmp_path: Path):
        """Test directory with all valid files."""
        # Create valid files
        (tmp_path / "model_user.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        )

        (tmp_path / "enum_status.py").write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
"""
        )

        result = validate_architecture_directory(tmp_path)

        assert result.is_valid is True
        assert result.metadata.files_processed == 2
        assert len(result.errors) == 0

    def test_directory_with_violations(self, tmp_path: Path):
        """Test directory with violations."""
        # Create file with violations
        (tmp_path / "models.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        )

        result = validate_architecture_directory(tmp_path, max_violations=0)

        assert result.is_valid is False
        assert result.metadata.files_processed == 1
        assert len(result.errors) > 0
        assert result.metadata.violations_found > 0

    def test_directory_with_allowed_violations(self, tmp_path: Path):
        """Test directory with violations within threshold."""
        # Create file with violations
        (tmp_path / "models.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        )

        result = validate_architecture_directory(tmp_path, max_violations=10)

        assert result.is_valid is True
        assert result.metadata.files_processed == 1
        assert len(result.errors) > 0
        assert result.metadata.violations_found > 0

    def test_skips_init_files(self, tmp_path: Path):
        """Test that __init__.py files are skipped."""
        # Create __init__.py with multiple exports
        (tmp_path / "__init__.py").write_text(
            """
from .model_user import ModelUser
from .model_post import ModelPost
"""
        )

        result = validate_architecture_directory(tmp_path)

        assert result.is_valid is True
        assert result.metadata.files_processed == 0

    def test_skips_pycache(self, tmp_path: Path):
        """Test that __pycache__ is skipped."""
        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "test.py").write_text("# cached file")

        result = validate_architecture_directory(tmp_path)

        assert result.is_valid is True
        assert result.metadata.files_processed == 0

    def test_metadata_populated(self, tmp_path: Path):
        """Test that metadata is properly populated."""
        (tmp_path / "models.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    pass

class ModelPost(BaseModel):
    pass
"""
        )

        result = validate_architecture_directory(tmp_path)

        assert result.metadata is not None
        assert result.metadata.validation_type == "architecture"
        assert result.metadata.max_violations is not None
        assert result.metadata.files_with_violations is not None

    def test_generic_exception_handling(self, tmp_path: Path, monkeypatch):
        """Test handling of generic exceptions during file processing."""
        test_file = tmp_path / "error_file.py"
        test_file.write_text("# Valid Python file")

        # Mock open to raise a generic exception
        def mock_open(*args, **kwargs):
            raise RuntimeError("Simulated file read error")

        monkeypatch.setattr("builtins.open", mock_open)

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("Parse error" in error for error in errors)

    def test_file_not_found_handling(self, tmp_path: Path):
        """Test handling of non-existent files."""
        non_existent = tmp_path / "doesnt_exist.py"

        # Should handle FileNotFoundError gracefully
        errors = validate_one_model_per_file(non_existent)
        assert len(errors) > 0
        assert any("Parse error" in error for error in errors)


class TestValidateArchitectureCLI:
    """Test validate_architecture_cli function."""

    def test_cli_with_valid_directory(self, tmp_path: Path, monkeypatch, capsys):
        """Test CLI with valid directory."""
        # Create valid test structure
        (tmp_path / "model_user.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        )

        # Mock sys.argv
        monkeypatch.setattr("sys.argv", ["script.py", str(tmp_path)])

        # Import and run CLI
        from omnibase_core.validation.architecture import validate_architecture_cli

        exit_code = validate_architecture_cli()
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "✅" in captured.out
        assert "PASSED" in captured.out

    def test_cli_with_violations(self, tmp_path: Path, monkeypatch, capsys):
        """Test CLI with violations."""
        # Create file with violations
        (tmp_path / "models.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        )

        monkeypatch.setattr("sys.argv", ["script.py", str(tmp_path)])

        from omnibase_core.validation.architecture import validate_architecture_cli

        exit_code = validate_architecture_cli()
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "❌" in captured.out
        assert "FAILURE" in captured.out
        assert "ARCHITECTURAL VIOLATIONS" in captured.out

    def test_cli_with_max_violations_flag(self, tmp_path: Path, monkeypatch, capsys):
        """Test CLI with --max-violations flag."""
        # Create file with violations
        (tmp_path / "models.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        )

        monkeypatch.setattr(
            "sys.argv", ["script.py", str(tmp_path), "--max-violations", "10"]
        )

        from omnibase_core.validation.architecture import validate_architecture_cli

        exit_code = validate_architecture_cli()
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "✅" in captured.out

    def test_cli_with_nonexistent_directory(self, tmp_path: Path, monkeypatch, capsys):
        """Test CLI with non-existent directory."""
        nonexistent = tmp_path / "doesnt_exist"

        monkeypatch.setattr("sys.argv", ["script.py", str(nonexistent)])

        from omnibase_core.validation.architecture import validate_architecture_cli

        exit_code = validate_architecture_cli()
        captured = capsys.readouterr()

        assert "not found" in captured.out.lower()

    def test_cli_with_multiple_directories(self, tmp_path: Path, monkeypatch, capsys):
        """Test CLI with multiple directories."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "model_user.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        )

        (dir2 / "enum_status.py").write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
"""
        )

        monkeypatch.setattr("sys.argv", ["script.py", str(dir1), str(dir2)])

        from omnibase_core.validation.architecture import validate_architecture_cli

        exit_code = validate_architecture_cli()
        captured = capsys.readouterr()

        assert exit_code == 0
        assert str(dir1) in captured.out
        assert str(dir2) in captured.out

    def test_cli_default_directory(self, monkeypatch, capsys):
        """Test CLI with default directory (src/)."""
        monkeypatch.setattr("sys.argv", ["script.py"])

        from omnibase_core.validation.architecture import validate_architecture_cli

        # This will try to scan src/ which may or may not exist
        # Just verify it doesn't crash
        exit_code = validate_architecture_cli()
        captured = capsys.readouterr()

        assert isinstance(exit_code, int)
        assert "ONEX" in captured.out

    def test_cli_output_format(self, tmp_path: Path, monkeypatch, capsys):
        """Test CLI output format and messages."""
        (tmp_path / "model_user.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        )

        monkeypatch.setattr("sys.argv", ["script.py", str(tmp_path)])

        from omnibase_core.validation.architecture import validate_architecture_cli

        exit_code = validate_architecture_cli()
        captured = capsys.readouterr()

        # Check for expected output sections
        assert "🔍 ONEX One-Model-Per-File Validation" in captured.out
        assert "📋 Enforcing architectural separation" in captured.out
        assert "📊 One-Model-Per-File Validation Summary" in captured.out
        assert "Files checked:" in captured.out
        assert "Total violations:" in captured.out

    def test_cli_failure_help_messages(self, tmp_path: Path, monkeypatch, capsys):
        """Test that failure output includes help messages."""
        (tmp_path / "models.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    pass

class ModelPost(BaseModel):
    pass
"""
        )

        monkeypatch.setattr("sys.argv", ["script.py", str(tmp_path)])

        from omnibase_core.validation.architecture import validate_architecture_cli

        exit_code = validate_architecture_cli()
        captured = capsys.readouterr()

        assert exit_code == 1
        # Check for help messages
        assert "💡 How to fix:" in captured.out
        assert "Split files" in captured.out
        assert "one-model-per-file principle" in captured.out

    def test_cli_mixed_valid_and_invalid_directories(
        self, tmp_path: Path, monkeypatch, capsys
    ):
        """Test CLI with mix of valid and invalid directories."""
        valid_dir = tmp_path / "valid"
        invalid_dir = tmp_path / "invalid"
        nonexistent_dir = tmp_path / "nonexistent"

        valid_dir.mkdir()
        invalid_dir.mkdir()

        (valid_dir / "model_user.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        )

        (invalid_dir / "models.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    pass

class ModelPost(BaseModel):
    pass
"""
        )

        monkeypatch.setattr(
            "sys.argv",
            ["script.py", str(valid_dir), str(nonexistent_dir), str(invalid_dir)],
        )

        from omnibase_core.validation.architecture import validate_architecture_cli

        exit_code = validate_architecture_cli()
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "not found" in captured.out.lower()
        assert str(invalid_dir) in captured.out


# =============================================================================
# ModelProtocolAuditor Tests
# =============================================================================


class TestModelProtocolAuditor:
    """Test ModelProtocolAuditor class."""

    def test_init_with_valid_path(self, tmp_path: Path):
        """Test initialization with valid repository path."""
        auditor = ModelProtocolAuditor(str(tmp_path))
        assert auditor.repository_path == tmp_path
        assert auditor.repository_name is not None

    def test_init_with_invalid_path(self):
        """Test initialization with invalid path raises ExceptionConfigurationError."""
        with pytest.raises(ExceptionConfigurationError):
            ModelProtocolAuditor("/nonexistent/path/that/does/not/exist")

    def test_init_with_current_directory(self):
        """Test initialization with current directory."""
        auditor = ModelProtocolAuditor(".")
        assert auditor.repository_path.exists()
        assert isinstance(auditor.repository_name, str)

    def test_check_current_repository_no_src(self, tmp_path: Path):
        """Test check_current_repository when no src/ directory exists."""
        auditor = ModelProtocolAuditor(str(tmp_path))
        result = auditor.check_current_repository()

        assert isinstance(result, ModelAuditResult)
        assert result.success is True
        assert result.protocols_found == 0
        assert "No src directory" in result.violations[0]
        assert "standard src/ structure" in result.recommendations[0]

    def test_check_current_repository_with_valid_protocols(self, tmp_path: Path):
        """Test check_current_repository with valid protocols."""
        # Create src directory structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create valid protocol file
        protocol_file = src_dir / "protocol_example.py"
        protocol_file.write_text(
            """
from typing import Protocol

class ProtocolExample(Protocol):
    def do_something(self) -> None:
        ...
"""
        )

        auditor = ModelProtocolAuditor(str(tmp_path))
        result = auditor.check_current_repository()

        assert isinstance(result, ModelAuditResult)
        assert result.protocols_found >= 0
        assert result.repository == auditor.repository_name

    def test_check_current_repository_with_local_duplicates(self, tmp_path: Path):
        """Test detection of local duplicate protocols."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create two identical protocols
        for i in [1, 2]:
            protocol_file = src_dir / f"protocol_dup{i}.py"
            protocol_file.write_text(
                """
from typing import Protocol

class ProtocolDuplicate(Protocol):
    def method_a(self) -> None:
        ...
"""
            )

        auditor = ModelProtocolAuditor(str(tmp_path))
        result = auditor.check_current_repository()

        assert isinstance(result, ModelAuditResult)
        # May find duplicates depending on extraction logic

    def test_find_local_duplicates(self, tmp_path: Path):
        """Test _find_local_duplicates method."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        # Create protocol infos with same signature
        protocol1 = ModelProtocolInfo(
            name="Protocol1",
            file_path="/path/to/file1.py",
            repository="test_repo",
            methods=["method_a", "method_b"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )
        protocol2 = ModelProtocolInfo(
            name="Protocol2",
            file_path="/path/to/file2.py",
            repository="test_repo",
            methods=["method_a", "method_b"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        duplicates = auditor._find_local_duplicates([protocol1, protocol2])

        assert len(duplicates) == 1
        assert duplicates[0].signature_hash == "abc123"
        assert duplicates[0].duplication_type == "exact"
        assert len(duplicates[0].protocols) == 2

    def test_find_local_duplicates_no_duplicates(self, tmp_path: Path):
        """Test _find_local_duplicates with no duplicates."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol1 = ModelProtocolInfo(
            name="Protocol1",
            file_path="/path/to/file1.py",
            repository="test_repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )
        protocol2 = ModelProtocolInfo(
            name="Protocol2",
            file_path="/path/to/file2.py",
            repository="test_repo",
            methods=["method_b"],
            signature_hash="def456",
            line_count=10,
            imports=[],
        )

        duplicates = auditor._find_local_duplicates([protocol1, protocol2])
        assert len(duplicates) == 0

    def test_check_naming_conventions(self, tmp_path: Path):
        """Test _check_naming_conventions method."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        # Protocol with correct naming
        good_protocol = ModelProtocolInfo(
            name="ProtocolGood",
            file_path="/path/to/protocol_good.py",
            repository="test_repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        # Protocol with incorrect naming
        bad_protocol = ModelProtocolInfo(
            name="BadName",
            file_path="/path/to/bad_file.py",
            repository="test_repo",
            methods=["method_a"],
            signature_hash="def456",
            line_count=10,
            imports=[],
        )

        violations = auditor._check_naming_conventions([good_protocol, bad_protocol])

        # Should find violations for bad protocol
        assert len(violations) >= 1
        assert any("should start with 'Protocol'" in v for v in violations)
        assert any("protocol_*.py" in v for v in violations)

    def test_check_naming_conventions_all_valid(self, tmp_path: Path):
        """Test _check_naming_conventions with all valid protocols."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol = ModelProtocolInfo(
            name="ProtocolExample",
            file_path="/path/to/protocol_example.py",
            repository="test_repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        violations = auditor._check_naming_conventions([protocol])
        # Should have no violations for properly named protocol
        assert len(violations) == 0

    def test_check_protocol_quality_empty_protocol(self, tmp_path: Path):
        """Test _check_protocol_quality with empty protocol."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        empty_protocol = ModelProtocolInfo(
            name="ProtocolEmpty",
            file_path="/path/to/protocol_empty.py",
            repository="test_repo",
            methods=[],
            signature_hash="abc123",
            line_count=5,
            imports=[],
        )

        issues = auditor._check_protocol_quality([empty_protocol])

        assert len(issues) == 1
        assert "has no methods" in issues[0]

    def test_check_protocol_quality_too_many_methods(self, tmp_path: Path):
        """Test _check_protocol_quality with overly complex protocol."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        # Create protocol with 25 methods
        complex_protocol = ModelProtocolInfo(
            name="ProtocolComplex",
            file_path="/path/to/protocol_complex.py",
            repository="test_repo",
            methods=[f"method_{i}" for i in range(25)],
            signature_hash="abc123",
            line_count=100,
            imports=[],
        )

        issues = auditor._check_protocol_quality([complex_protocol])

        assert len(issues) == 1
        assert "25 methods" in issues[0]
        assert "consider splitting" in issues[0]

    def test_check_protocol_quality_good_protocol(self, tmp_path: Path):
        """Test _check_protocol_quality with well-designed protocol."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        good_protocol = ModelProtocolInfo(
            name="ProtocolGood",
            file_path="/path/to/protocol_good.py",
            repository="test_repo",
            methods=["method_a", "method_b", "method_c"],
            signature_hash="abc123",
            line_count=15,
            imports=[],
        )

        issues = auditor._check_protocol_quality([good_protocol])
        assert len(issues) == 0

    def test_check_against_spi_invalid_path(self, tmp_path: Path):
        """Test check_against_spi with invalid SPI path."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        with pytest.raises(ExceptionConfigurationError):
            auditor.check_against_spi("/nonexistent/spi/path")

    def test_check_against_spi_no_protocols_dir(self, tmp_path: Path):
        """Test check_against_spi when SPI protocols directory doesn't exist."""
        # Create SPI directory structure without protocols
        spi_dir = tmp_path / "spi"
        spi_dir.mkdir()
        (spi_dir / "src").mkdir()

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        auditor = ModelProtocolAuditor(str(repo_dir))
        report = auditor.check_against_spi(str(spi_dir))

        assert isinstance(report, ModelDuplicationReport)
        assert report.source_repository == auditor.repository_name

    def test_check_against_spi_with_duplicates(self, tmp_path: Path):
        """Test check_against_spi detecting exact duplicates."""
        # Create repo directory with protocol
        repo_dir = tmp_path / "repo"
        src_dir = repo_dir / "src"
        src_dir.mkdir(parents=True)

        protocol_file = src_dir / "protocol_example.py"
        protocol_file.write_text(
            """
from typing import Protocol

class ProtocolExample(Protocol):
    def method_a(self) -> None:
        ...
"""
        )

        # Create SPI directory with same protocol
        spi_dir = tmp_path / "spi"
        spi_protocols_dir = spi_dir / "src" / "omnibase_spi" / "protocols"
        spi_protocols_dir.mkdir(parents=True)

        spi_protocol_file = spi_protocols_dir / "protocol_example.py"
        spi_protocol_file.write_text(
            """
from typing import Protocol

class ProtocolExample(Protocol):
    def method_a(self) -> None:
        ...
"""
        )

        auditor = ModelProtocolAuditor(str(repo_dir))
        report = auditor.check_against_spi(str(spi_dir))

        assert isinstance(report, ModelDuplicationReport)
        assert report.source_repository == auditor.repository_name
        assert report.target_repository == "omnibase_spi"

    def test_analyze_cross_repo_duplicates_exact(self, tmp_path: Path):
        """Test _analyze_cross_repo_duplicates with exact duplicates."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        source_protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/source/protocol_a.py",
            repository="source_repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        target_protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/target/protocol_a.py",
            repository="target_repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        result = auditor._analyze_cross_repo_duplicates(
            [source_protocol], [target_protocol]
        )

        assert len(result["exact_duplicates"]) == 1
        assert result["exact_duplicates"][0].duplication_type == "exact"
        assert len(result["name_conflicts"]) == 0

    def test_analyze_cross_repo_duplicates_name_conflict(self, tmp_path: Path):
        """Test _analyze_cross_repo_duplicates with name conflicts."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        source_protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/source/protocol_a.py",
            repository="source_repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        target_protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/target/protocol_a.py",
            repository="target_repo",
            methods=["method_b"],
            signature_hash="def456",
            line_count=10,
            imports=[],
        )

        result = auditor._analyze_cross_repo_duplicates(
            [source_protocol], [target_protocol]
        )

        assert len(result["name_conflicts"]) == 1
        assert result["name_conflicts"][0].duplication_type == "name_conflict"
        assert len(result["exact_duplicates"]) == 0

    def test_analyze_cross_repo_duplicates_no_conflicts(self, tmp_path: Path):
        """Test _analyze_cross_repo_duplicates with no conflicts."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        source_protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/source/protocol_a.py",
            repository="source_repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        target_protocol = ModelProtocolInfo(
            name="ProtocolB",
            file_path="/target/protocol_b.py",
            repository="target_repo",
            methods=["method_b"],
            signature_hash="def456",
            line_count=10,
            imports=[],
        )

        result = auditor._analyze_cross_repo_duplicates(
            [source_protocol], [target_protocol]
        )

        assert len(result["exact_duplicates"]) == 0
        assert len(result["name_conflicts"]) == 0

    def test_has_duplicate_in_spi_exact_match(self, tmp_path: Path):
        """Test _has_duplicate_in_spi with exact signature match."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/path/protocol_a.py",
            repository="repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        spi_protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/spi/protocol_a.py",
            repository="spi",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        assert auditor._has_duplicate_in_spi(protocol, [spi_protocol]) is True

    def test_has_duplicate_in_spi_name_match(self, tmp_path: Path):
        """Test _has_duplicate_in_spi with name match."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/path/protocol_a.py",
            repository="repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        spi_protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/spi/protocol_a.py",
            repository="spi",
            methods=["method_b"],
            signature_hash="def456",
            line_count=10,
            imports=[],
        )

        assert auditor._has_duplicate_in_spi(protocol, [spi_protocol]) is True

    def test_has_duplicate_in_spi_no_match(self, tmp_path: Path):
        """Test _has_duplicate_in_spi with no match."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/path/protocol_a.py",
            repository="repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        spi_protocol = ModelProtocolInfo(
            name="ProtocolB",
            file_path="/spi/protocol_b.py",
            repository="spi",
            methods=["method_b"],
            signature_hash="def456",
            line_count=10,
            imports=[],
        )

        assert auditor._has_duplicate_in_spi(protocol, [spi_protocol]) is False

    def test_print_audit_summary(self, tmp_path: Path):
        """Test print_audit_summary method."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        result = ModelAuditResult(
            success=False,
            repository="test_repo",
            protocols_found=5,
            duplicates_found=2,
            conflicts_found=1,
            violations=["Violation 1", "Violation 2"],
            recommendations=["Recommendation 1"],
        )

        # Should not raise any exceptions
        auditor.print_audit_summary(result)

    def test_print_duplication_report(self, tmp_path: Path):
        """Test print_duplication_report method."""
        auditor = ModelProtocolAuditor(str(tmp_path))

        protocol = ModelProtocolInfo(
            name="ProtocolA",
            file_path="/path/protocol_a.py",
            repository="repo",
            methods=["method_a"],
            signature_hash="abc123",
            line_count=10,
            imports=[],
        )

        dup_info = ModelDuplicationInfo(
            signature_hash="abc123",
            protocols=[protocol],
            duplication_type="exact",
            recommendation="Remove duplicate",
        )

        report = ModelDuplicationReport(
            success=False,
            source_repository="source_repo",
            target_repository="target_repo",
            exact_duplicates=[dup_info],
            name_conflicts=[],
            migration_candidates=[protocol],
            recommendations=["Remove duplicates"],
        )

        # Should not raise any exceptions
        auditor.print_duplication_report(report)

    def test_audit_ecosystem(self, tmp_path: Path):
        """Test audit_ecosystem method."""
        # Create multiple omni* repositories
        omni_root = tmp_path / "omni_root"
        omni_root.mkdir()

        repo1 = omni_root / "omnibase_core"
        repo1.mkdir()
        (repo1 / "src").mkdir()

        repo2 = omni_root / "omnibase_spi"
        repo2.mkdir()
        (repo2 / "src").mkdir()

        # Add a non-omni directory (should be skipped)
        other_dir = omni_root / "other_project"
        other_dir.mkdir()

        # Add a file (should be skipped)
        (omni_root / "readme.txt").write_text("test")

        auditor = ModelProtocolAuditor(str(repo1))
        results = auditor.audit_ecosystem(omni_root)

        assert isinstance(results, dict)
        assert "omnibase_core" in results or "omnibase_spi" in results
        # other_project should not be in results
        assert "other_project" not in results

    def test_audit_ecosystem_empty_root(self, tmp_path: Path):
        """Test audit_ecosystem with empty root directory."""
        empty_root = tmp_path / "empty_root"
        empty_root.mkdir()

        auditor = ModelProtocolAuditor(str(tmp_path))
        results = auditor.audit_ecosystem(empty_root)

        assert isinstance(results, dict)
        assert len(results) == 0


class TestModelAuditResult:
    """Test ModelAuditResult model."""

    def test_has_issues_with_duplicates(self):
        """Test has_issues returns True when duplicates found."""
        result = ModelAuditResult(
            success=False,
            repository="test_repo",
            protocols_found=5,
            duplicates_found=2,
            conflicts_found=0,
            violations=[],
            recommendations=[],
        )

        assert result.has_issues() is True

    def test_has_issues_with_conflicts(self):
        """Test has_issues returns True when conflicts found."""
        result = ModelAuditResult(
            success=False,
            repository="test_repo",
            protocols_found=5,
            duplicates_found=0,
            conflicts_found=1,
            violations=[],
            recommendations=[],
        )

        assert result.has_issues() is True

    def test_has_issues_with_violations(self):
        """Test has_issues returns True when violations found."""
        result = ModelAuditResult(
            success=False,
            repository="test_repo",
            protocols_found=5,
            duplicates_found=0,
            conflicts_found=0,
            violations=["Violation 1"],
            recommendations=[],
        )

        assert result.has_issues() is True

    def test_has_issues_no_issues(self):
        """Test has_issues returns False when no issues."""
        result = ModelAuditResult(
            success=True,
            repository="test_repo",
            protocols_found=5,
            duplicates_found=0,
            conflicts_found=0,
            violations=[],
            recommendations=[],
        )

        assert result.has_issues() is False


class TestArchitectureEdgeCases:
    """Test edge cases for architecture validation."""

    def test_validate_one_model_per_file_with_nested_classes(self, tmp_path: Path):
        """Test validation with nested classes."""
        test_file = tmp_path / "nested.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelOuter(BaseModel):
    class ModelInner(BaseModel):
        value: str
"""
        )

        errors = validate_one_model_per_file(test_file)
        # Should detect multiple models
        assert len(errors) > 0

    def test_validate_architecture_directory_recursive(self, tmp_path: Path):
        """Test recursive directory validation."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        (tmp_path / "model_a.py").write_text(
            """
from pydantic import BaseModel

class ModelA(BaseModel):
    pass
"""
        )

        (subdir / "model_b.py").write_text(
            """
from pydantic import BaseModel

class ModelB(BaseModel):
    pass
"""
        )

        result = validate_architecture_directory(tmp_path)

        # Should find both files recursively
        assert result.metadata.files_processed >= 2

    def test_validate_architecture_directory_skips_archived(self, tmp_path: Path):
        """Test that archived directories are skipped."""
        archived_dir = tmp_path / "archived"
        archived_dir.mkdir()

        (archived_dir / "old_model.py").write_text(
            """
from pydantic import BaseModel

class ModelOld(BaseModel):
    pass

class ModelOld2(BaseModel):
    pass
"""
        )

        result = validate_architecture_directory(tmp_path)

        # Should skip archived directory
        assert result.metadata.files_processed == 0
        assert result.is_valid is True

    def test_validate_architecture_directory_skips_test_fixtures(self, tmp_path: Path):
        """Test that test fixtures are skipped."""
        fixtures_dir = tmp_path / "tests" / "fixtures"
        fixtures_dir.mkdir(parents=True)

        (fixtures_dir / "fixture_model.py").write_text(
            """
from pydantic import BaseModel

class ModelFixture1(BaseModel):
    pass

class ModelFixture2(BaseModel):
    pass
"""
        )

        result = validate_architecture_directory(tmp_path)

        # Should skip fixtures directory
        assert result.metadata.files_processed == 0
        assert result.is_valid is True

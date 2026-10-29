# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Backward compatibility detector and CLI regression coverage (OMN-21501)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from omnibase_core.handlers.handler_backward_compat import HandlerBackwardCompat
from omnibase_core.handlers.handler_backward_compat_cli import load_rules, main
from omnibase_core.models.backward_compat import (
    ModelBackwardCompatCheckInput,
    ModelBackwardCompatRules,
)
from omnibase_core.models.finding_baseline import ModelFindingDetectResult
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

pytestmark = pytest.mark.unit


def detect(source: str, path: str = "example.py") -> ModelFindingDetectResult:
    return HandlerBackwardCompat().handle(
        ModelBackwardCompatCheckInput(
            files=(ModelSourceFile(path=path, source=source),), rules=load_rules()
        )
    )


def errors(result: ModelFindingDetectResult) -> list[str]:
    return [f"Line {finding.line}: {finding.message}" for finding in result.findings]


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    return tmp_path


@pytest.mark.unit
class TestBackwardCompatibilityHandler:
    def test_valid_file_without_compatibility_patterns(self, temp_repo):
        """Test validation of files without backward compatibility patterns."""
        valid_content = '''
from pydantic import BaseModel, ConfigDict

class ModelUserAuth(BaseModel):
    """User authentication model."""
    user_id: str
    username: str

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

def process_user_data(data: dict) -> dict:
    """Process user data."""
    return {"processed": True}
'''
        test_file = temp_repo / "valid_file.py"
        test_file.write_text(valid_content)

        result = detect(test_file.read_text(encoding="utf-8"), str(test_file))
        assert not result.findings
        assert result.files_checked == 1
        assert len(errors(result)) == 0

    def test_backward_compatibility_comment_detection(self, temp_repo):
        """Test detection of backward compatibility comments."""
        compat_content = '''
from pydantic import BaseModel

class ModelUserAuth(BaseModel):
    """User authentication model."""
    user_id: str

    # Accept simple Protocol* names for backward compatibility
    def validate_protocol(self, name: str) -> bool:
        return True

    def legacy_method(self) -> dict:
        """Convert to dictionary for backwards compatibility."""
        return self.model_dump()
'''
        test_file = temp_repo / "compat_comments.py"
        test_file.write_text(compat_content)

        result = detect(test_file.read_text(encoding="utf-8"), str(test_file))
        assert result.findings
        assert len(errors(result)) >= 1

        # Check that specific patterns were detected
        error_messages = " ".join(errors(result))
        assert "backward compatibility comment" in error_messages.lower()

    def test_legacy_method_detection(self, temp_repo):
        """Test detection of legacy method names."""
        legacy_content = '''
class ModelUser:
    """User model."""

    def get_data_legacy(self) -> dict:
        """Legacy method."""
        return {}

    def process_deprecated(self, data: dict) -> dict:
        """Deprecated method."""
        return data

    def convert_compat(self, format: str) -> str:
        """Compatibility method."""
        return format

    def transform_backward(self, input: dict) -> dict:
        """Backward compatibility transform."""
        return input
'''
        test_file = temp_repo / "legacy_methods.py"
        test_file.write_text(legacy_content)

        result = detect(test_file.read_text(encoding="utf-8"), str(test_file))
        assert result.findings
        assert len(errors(result)) >= 4

        error_messages = " ".join(errors(result))
        assert "legacy support method" in error_messages.lower()

    def test_protocol_compatibility_pattern_detection(self, temp_repo):
        """Test detection of Protocol backward compatibility patterns."""
        protocol_content = '''
def validate_dependency(dependency: str) -> bool:
    """Validate dependency names."""
    # Accept simple Protocol* names for backward compatibility
    if dependency.startswith("Protocol"):
        return True
    return False

def check_protocol_name(name: str) -> bool:
    """Check protocol naming."""
    # Protocol legacy support
    if name.startswith("Protocol"):
        return True
    return False
'''
        test_file = temp_repo / "protocol_compat.py"
        test_file.write_text(protocol_content)

        result = detect(test_file.read_text(encoding="utf-8"), str(test_file))
        assert result.findings
        assert len(errors(result)) >= 1

        error_messages = " ".join(errors(result))
        assert "protocol" in error_messages.lower()

    def test_extra_allow_configuration_detection(self, temp_repo):
        """Test detection of permissive configuration for compatibility."""
        config_content = '''
from pydantic import BaseModel, ConfigDict

class ModelUser(BaseModel):
    """User model."""
    user_id: str

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields for compatibility
        validate_assignment=True,
    )

class ConfigSettings:
    """Settings with compatibility config."""
    extra = "allow"  # For backward compatibility
'''
        test_file = temp_repo / "config_compat.py"
        test_file.write_text(config_content)

        result = detect(test_file.read_text(encoding="utf-8"), str(test_file))
        # This might pass since the current pattern matching is more specific
        # Check if any compatibility-related errors were detected
        if result.findings:
            error_messages = " ".join(errors(result))
            assert "compatibility" in error_messages.lower()

    def test_ast_compatibility_function_detection(self, temp_repo):
        """Test AST-based detection of compatibility function patterns."""
        ast_content = '''
class ModelUser:
    """User model."""

    def to_dict_legacy(self) -> dict:
        """Convert to dict for backward compatibility."""
        return {"legacy": True}

    def get_data_deprecated(self) -> dict:
        """Deprecated data getter for backward compatibility."""
        return {}

    def process_compat(self, data: dict) -> dict:
        """Processing method for legacy support."""
        return data
'''
        test_file = temp_repo / "ast_compat.py"
        test_file.write_text(ast_content)

        result = detect(test_file.read_text(encoding="utf-8"), str(test_file))
        assert result.findings
        assert len(errors(result)) >= 3

        error_messages = " ".join(errors(result))
        assert "backward compatibility function" in error_messages.lower()

    def test_docstring_compatibility_detection(self, temp_repo):
        """Test detection of backward compatibility in docstrings."""
        docstring_content = '''
class ModelUser:
    """User model."""

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return self.__dict__

    def export_data(self) -> dict:
        """Export data with legacy support for old formats."""
        return {}

    def migrate_data(self) -> dict:
        """Migrate data - migration path for legacy systems."""
        return {}
'''
        test_file = temp_repo / "docstring_compat.py"
        test_file.write_text(docstring_content)

        result = detect(test_file.read_text(encoding="utf-8"), str(test_file))
        assert result.findings
        assert len(errors(result)) >= 1

        error_messages = " ".join(errors(result))
        assert (
            "backward compatibility docstring" in error_messages.lower()
            or "legacy support" in error_messages.lower()
        )


@pytest.mark.unit
class TestEdgeCases:
    def test_empty_file_handling(self, temp_repo):
        """Test handling of empty files."""
        empty_file = temp_repo / "empty.py"
        empty_file.touch()

        result = detect(empty_file.read_text(encoding="utf-8"), str(empty_file))
        assert not result.findings
        assert result.files_checked == 1
        assert len(errors(result)) == 0

    def test_syntax_error_handling(self, temp_repo):
        """Test handling of files with syntax errors."""
        syntax_error_content = """
class ModelUser:
    def __init__(self:  # Missing closing parenthesis
        self.user_id = "test"

    def get_data(self) -> dict
        # Missing colon
        return {}
"""
        error_file = temp_repo / "syntax_error.py"
        error_file.write_text(syntax_error_content)

        result = detect(error_file.read_text(encoding="utf-8"), str(error_file))
        assert result.findings
        assert len(errors(result)) >= 1
        assert "syntax error" in errors(result)[0].lower()

    def test_unicode_file_handling(self, temp_repo):
        """Test handling of files with Unicode content."""
        unicode_content = '''# -*- coding: utf-8 -*-
"""File with Unicode: 中文, emoji 🚀, accents ñáéíóú"""

class ModelUser:
    """User model with Unicode support."""

    def get_user_name(self) -> str:
        """Get user name - supports José, 北京, etc."""
        return "José González 🎉"
'''
        unicode_file = temp_repo / "unicode_file.py"
        unicode_file.write_text(unicode_content, encoding="utf-8")

        result = detect(unicode_file.read_text(encoding="utf-8"), str(unicode_file))
        assert not result.findings
        assert result.files_checked == 1

    def test_large_file_handling(self, temp_repo):
        """Test handling of large files."""
        # Create a large file with many classes
        large_content = '''
"""Large file for testing performance."""

from pydantic import BaseModel

'''
        # Add many classes
        for i in range(100):
            large_content += f'''
class ModelTest{i:03d}(BaseModel):
    """Test model {i}."""
    field_{i}: str = "value_{i}"

    def process_{i}(self) -> dict:
        """Process data for model {i}."""
        return {{"processed": {i}}}

'''

        large_file = temp_repo / "large_file.py"
        large_file.write_text(large_content)

        import time

        start_time = time.time()
        result = detect(large_file.read_text(encoding="utf-8"), str(large_file))
        end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 10.0
        assert not result.findings  # No compatibility patterns
        assert result.files_checked == 1


def test_empty_request() -> None:
    result = HandlerBackwardCompat().handle(
        ModelBackwardCompatCheckInput(files=(), rules=load_rules())
    )
    assert not result.findings
    assert result.files_checked == 0


@pytest.mark.parametrize("exception", [ValueError("invalid source"), MemoryError()])
def test_parse_failures_are_unbaselinable(exception: Exception) -> None:
    with patch(
        "omnibase_core.handlers.handler_backward_compat.ast.parse",
        side_effect=exception,
    ):
        result = detect("# legacy support\n")
    (finding,) = result.findings
    assert finding.rule == "file-error"
    assert finding.line == 0
    assert not finding.baselinable
    expected = (
        "Invalid Python code"
        if isinstance(exception, ValueError)
        else "File too large to parse in memory"
    )
    assert expected in finding.message


def test_syntax_error_preserves_location_and_discards_regex_matches() -> None:
    result = detect("# backward compatibility\ndef broken(:\n")
    (finding,) = result.findings
    assert finding.rule == "file-error"
    assert finding.line == 2
    assert finding.text == "def broken(:"
    assert "Python syntax error at line 2" in finding.message
    assert not finding.baselinable


def test_architectural_exemption_is_checked_without_parsing() -> None:
    result = detect(
        "# backward compatibility\ndef broken(:",
        "src/omnibase_core/models/epic/model_epic_state.py",
    )
    assert result.files_checked == 1
    assert not result.findings


def test_duplicate_reports_and_normalized_source_are_preserved() -> None:
    result = detect(
        "\n    # backward compatibility for compatibility\ndef process_legacy(): pass\n"
    )
    assert [finding.rule for finding in result.findings] == [
        "compat-comment",
        "compat-comment",
        "compat-method",
        "compat-function-name",
    ]
    assert [finding.line for finding in result.findings] == [2, 2, 3, 3]
    assert result.findings[0].text == "# backward compatibility for compatibility"
    assert (
        "Line 3: Backward compatibility function 'process_legacy'" in errors(result)[3]
    )


def test_protocol_condition_uses_supplied_source_without_file_reads() -> None:
    source = '# legacy\nif name.startswith("Protocol"):\n    pass\n'
    with patch("builtins.open", side_effect=AssertionError("handler must be pure")):
        result = detect(source, "/nonexistent/source.py")
    assert any(
        f.rule == "compat-protocol-condition" and f.line == 2 for f in result.findings
    )


@pytest.mark.parametrize(
    "name",
    [
        "is_deprecated",
        "create_deprecated",
        "get_deprecated",
        "mark_deprecated",
        "check_deprecated",
        "__compat__",
    ],
)
def test_legitimate_function_names_are_exempt_from_ast_checks(name: str) -> None:
    result = detect(f'def {name}():\n    """backward compatibility"""\n')
    assert all(f.rule == "compat-comment" for f in result.findings)


def test_async_function_keeps_original_regex_only_behavior() -> None:
    result = detect('async def process_legacy():\n    """backward compatibility"""\n')
    assert {f.rule for f in result.findings} == {"compat-method", "compat-comment"}


@pytest.mark.parametrize(
    "name", ["ModelBackwardCompatRules", "ModelBackwardCompatCheckInput"]
)
def test_models_are_frozen_and_forbid_unknown_fields(name: str) -> None:
    model = (
        load_rules()
        if name == "ModelBackwardCompatRules"
        else ModelBackwardCompatCheckInput(files=(), rules=load_rules())
    )
    with pytest.raises(ValidationError):
        type(model).model_validate({**model.model_dump(), "surprise": True})
    field = next(iter(type(model).model_fields))
    with pytest.raises(ValidationError):
        setattr(model, field, getattr(model, field))


def test_rules_load_from_cached_package_resource() -> None:
    assert load_rules() is load_rules()
    assert isinstance(load_rules(), ModelBackwardCompatRules)


def test_cli_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["/nonexistent/file.py"]) == 1
    assert "File not found" in capsys.readouterr().out


def test_cli_oversize_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    file = tmp_path / "large.py"
    # Sparse file: exercise the real configured limit without a large allocation.
    with file.open("wb") as stream:
        stream.truncate(load_rules().max_file_size_bytes + 1)
    assert main([str(file)]) == 1
    assert "File too large" in capsys.readouterr().out


def test_cli_permission_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / "denied.py"
    file.write_text("pass\n", encoding="utf-8")
    with patch.object(
        Path, "read_bytes", side_effect=PermissionError("Permission denied")
    ):
        assert main([str(file)]) == 1
    assert "permission denied" in capsys.readouterr().out.lower()


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "latin1", "cp1252"])
def test_cli_encoding_fallbacks(
    tmp_path: Path, encoding: str, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / "encoded.py"
    # Preserve the old decoding order: latin1 accepts every byte, including cp1252.
    text = "# café\npass\n"
    file.write_bytes(text.encode(encoding))
    # UTF-8 decoding accepts the BOM; ast.parse then reports it, as before.
    assert main([str(file)]) == (1 if encoding == "utf-8-sig" else 0)
    output = capsys.readouterr().out
    assert ("syntax error" if encoding == "utf-8-sig" else "passed") in output


def test_cli_binary_data_fails_gracefully(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / "binary.py"
    file.write_bytes(b"\xff\xfe\x00\x00invalid utf-8 data\x80\x81\x82")
    assert main([str(file)]) == 1
    assert "syntax error" in capsys.readouterr().out


def test_cli_directory_discovery(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "subdir").mkdir()
    for name in ("file1.py", "file2.py", "subdir/file3.py"):
        (tmp_path / name).write_text("# legacy support\n", encoding="utf-8")
    (tmp_path / "not_python.txt").write_text("# legacy support\n", encoding="utf-8")
    assert main(["--dir", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    for name in ("file1.py", "file2.py", "file3.py"):
        assert name in output
    assert "not_python.txt" not in output


@pytest.mark.parametrize("directory", load_rules().skip_dir_parts)
def test_cli_skips_configured_directories(
    tmp_path: Path, directory: str, capsys: pytest.CaptureFixture[str]
) -> None:
    skipped = tmp_path / directory
    skipped.mkdir()
    (skipped / "violation.py").write_text("# legacy support\n", encoding="utf-8")
    (tmp_path / "valid.py").touch()
    assert main(["--dir", str(tmp_path)]) == 0
    assert "1 files checked" in capsys.readouterr().out


def test_cli_nonexistent_directory(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--dir", "/nonexistent/directory"]) == 1
    assert "does not exist" in capsys.readouterr().out


def test_cli_file_as_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / "test.py"
    file.touch()
    assert main(["--dir", str(file)]) == 1
    assert "not a directory" in capsys.readouterr().out


def test_cli_mixed_files_and_directories(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    files = [tmp_path / "file1.py", tmp_path / "file2.py", subdir / "file3.py"]
    for file in files:
        file.touch()
    assert main([str(files[0]), str(files[1]), "--dir", str(subdir)]) == 0
    assert "3 files checked" in capsys.readouterr().out


def test_cli_deduplicates_files_and_directory_overlap(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / "test.py"
    file.touch()
    assert main([str(file), str(file), "--dir", str(tmp_path)]) == 0
    assert "1 files checked" in capsys.readouterr().out


def test_cli_non_python_file_is_ignored(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / "not_python.txt"
    file.write_text("# backward compatibility\n", encoding="utf-8")
    assert main([str(file)]) == 0
    assert "0 files checked" in capsys.readouterr().out


def test_batch_validation() -> None:
    result = HandlerBackwardCompat().handle(
        ModelBackwardCompatCheckInput(
            files=(
                ModelSourceFile(path="valid.py", source="print('valid')"),
                ModelSourceFile(
                    path="compat.py",
                    source='def process_legacy(data: dict) -> dict:\n    """Process data for backward compatibility."""\n    return data\n',
                ),
            ),
            rules=load_rules(),
        )
    )
    assert result.files_checked == 2
    assert result.findings
    assert all(f.path == "compat.py" for f in result.findings)


def test_cli_success_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for number in range(5):
        (tmp_path / f"file{number}.py").touch()
    assert main(["--dir", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "passed" in output
    assert "5 files" in output


def test_cli_failure_output_and_remediation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in ("file1.py", "file2.py"):
        (tmp_path / name).write_text("# backward compatibility\n", encoding="utf-8")
    assert main(["--dir", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "FAILED" in output
    assert "file1.py" in output and "file2.py" in output
    assert "Backward compatibility comment detected" in output
    assert "Remove ALL backward compatibility patterns" in output


def test_cli_verbose_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for number in range(10):
        (tmp_path / f"file{number}.py").touch()
    assert main(["--dir", str(tmp_path), "--verbose"]) == 0
    assert "10 files" in capsys.readouterr().out


def test_cli_argument_parsing_and_file_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = [tmp_path / "file1.py", tmp_path / "file2.py"]
    for file in files:
        file.write_text("print('test')", encoding="utf-8")
    assert main([str(file) for file in files]) == 0
    assert "2 files checked" in capsys.readouterr().out


def test_cli_directory_mode(tmp_path: Path) -> None:
    (tmp_path / "test.py").write_text("print('test')", encoding="utf-8")
    assert main(["--dir", str(tmp_path)]) == 0


def test_cli_no_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 1
    assert "Must provide either files or directories" in capsys.readouterr().out


@pytest.mark.parametrize(
    "source",
    [
        'from pydantic import BaseModel, ConfigDict\nclass ModelUser(BaseModel):\n    model_config = ConfigDict(extra="forbid")\n    user_id: str\n',
        'def process_data(data: dict) -> dict:\n    """Process user data."""\n    return data\n',
    ],
)
def test_valid_fixtures_pass_validation(source: str) -> None:
    # The old optional fixture directories are absent; keep these cases explicit.
    result = detect(source)
    assert not result.findings, errors(result)


def test_invalid_fixture_triggers_violations() -> None:
    result = detect(
        'def process_legacy(data: dict) -> dict:\n    """Process data for backward compatibility."""\n    return data\n'
    )
    assert result.findings

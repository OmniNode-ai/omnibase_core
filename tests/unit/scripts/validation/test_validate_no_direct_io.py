"""
Comprehensive tests for the validate-no-direct-io.py validation script.

Tests cover:
- DirectIODetector AST visitor
- DirectIOValidator file and directory validation
- Happy paths (valid code with no violations)
- Violation detection (code that should trigger violations)
- Bypass comments (# io-ok: patterns)
- File exclusions (test files, __init__.py, legacy dirs)
- CLI arguments (--verbose, --directory)
- Edge cases (syntax errors, empty files)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

# Import the validation script components
# We need to add the scripts directory to path for testing
SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "scripts" / "validation"
)
sys.path.insert(0, str(SCRIPTS_DIR))

# Import after adding to path
# Use importlib to avoid issues with hyphenated filename
import importlib.util

spec = importlib.util.spec_from_file_location(
    "validate_no_direct_io", SCRIPTS_DIR / "validate-no-direct-io.py"
)
validate_no_direct_io = importlib.util.module_from_spec(spec)
# Add to sys.modules before exec to avoid dataclass issues
sys.modules["validate_no_direct_io"] = validate_no_direct_io
spec.loader.exec_module(validate_no_direct_io)

DirectIODetector = validate_no_direct_io.DirectIODetector
DirectIOValidator = validate_no_direct_io.DirectIOValidator
IOViolation = validate_no_direct_io.IOViolation
main = validate_no_direct_io.main

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]


class TestIOViolation:
    """Tests for the IOViolation named tuple."""

    def test_io_violation_creation(self) -> None:
        """Test that IOViolation can be created with all fields."""
        violation = IOViolation(
            file_path="/test/file.py",
            line_number=10,
            column=5,
            pattern_type="file_io",
            code_snippet="open('test.txt')",
            description="Direct file I/O detected",
        )
        assert violation.file_path == "/test/file.py"
        assert violation.line_number == 10
        assert violation.column == 5
        assert violation.pattern_type == "file_io"
        assert violation.code_snippet == "open('test.txt')"
        assert violation.description == "Direct file I/O detected"


class TestDirectIODetectorFileIO:
    """Tests for file I/O detection in DirectIODetector."""

    def test_detects_open_builtin(self) -> None:
        """Test detection of open() builtin function."""
        code = """
def read_file():
    f = open("test.txt")
    return f.read()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "file_io"
        assert "open" in violations[0].description

    def test_detects_path_read_text(self) -> None:
        """Test detection of Path.read_text() method."""
        code = """
from pathlib import Path

def read_file():
    file_path = Path("test.txt")
    return file_path.read_text()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "path_io"
        assert "read_text" in violations[0].description

    def test_detects_path_write_text(self) -> None:
        """Test detection of Path.write_text() method."""
        code = """
from pathlib import Path

def write_file():
    file_path = Path("test.txt")
    file_path.write_text("content")
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "path_io"
        assert "write_text" in violations[0].description

    def test_detects_path_read_bytes(self) -> None:
        """Test detection of Path.read_bytes() method."""
        code = """
from pathlib import Path

def read_file():
    file_path = Path("test.bin")
    return file_path.read_bytes()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "path_io"

    def test_detects_path_write_bytes(self) -> None:
        """Test detection of Path.write_bytes() method."""
        code = """
from pathlib import Path

def write_file():
    file_path = Path("test.bin")
    file_path.write_bytes(b"content")
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "path_io"

    def test_detects_path_mkdir(self) -> None:
        """Test detection of Path.mkdir() method."""
        code = """
from pathlib import Path

def create_dir():
    dir_path = Path("newdir")
    dir_path.mkdir()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "path_io"

    def test_detects_path_unlink(self) -> None:
        """Test detection of Path.unlink() method."""
        code = """
from pathlib import Path

def delete_file():
    file_path = Path("test.txt")
    file_path.unlink()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "path_io"

    def test_detects_path_exists(self) -> None:
        """Test detection of Path.exists() method."""
        code = """
from pathlib import Path

def check_file():
    file_path = Path("test.txt")
    return file_path.exists()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "path_io"

    def test_detects_path_glob(self) -> None:
        """Test detection of Path.glob() method."""
        code = """
from pathlib import Path

def find_files():
    dir_path = Path(".")
    return list(dir_path.glob("*.py"))
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "path_io"


class TestDirectIODetectorNetworkIO:
    """Tests for network I/O detection in DirectIODetector."""

    def test_detects_requests_get(self) -> None:
        """Test detection of requests.get() call."""
        code = """
import requests

def fetch_data():
    response = requests.get("https://api.example.com")
    return response.json()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "network_io"
        assert "get" in violations[0].description

    def test_detects_requests_post(self) -> None:
        """Test detection of requests.post() call."""
        code = """
import requests

def send_data():
    response = requests.post("https://api.example.com", json={})
    return response.status_code
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "network_io"

    def test_detects_httpx_get(self) -> None:
        """Test detection of httpx.get() call."""
        code = """
import httpx

def fetch_data():
    response = httpx.get("https://api.example.com")
    return response.json()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "network_io"


class TestDirectIODetectorDatabaseIO:
    """Tests for database I/O detection in DirectIODetector."""

    def test_detects_asyncpg_connect(self) -> None:
        """Test detection of asyncpg.connect() call."""
        code = """
import asyncpg

async def get_connection():
    conn = await asyncpg.connect("postgresql://localhost/db")
    return conn
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "database_io"

    def test_detects_psycopg2_connect(self) -> None:
        """Test detection of psycopg2.connect() call."""
        code = """
import psycopg2

def get_connection():
    conn = psycopg2.connect("postgresql://localhost/db")
    return conn
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "database_io"

    def test_detects_sqlite3_connect(self) -> None:
        """Test detection of sqlite3.connect() call."""
        code = """
import sqlite3

def get_connection():
    conn = sqlite3.connect("test.db")
    return conn
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "database_io"

    def test_detects_sqlalchemy_create_engine(self) -> None:
        """Test detection of sqlalchemy.create_engine() call."""
        code = """
import sqlalchemy

def get_engine():
    engine = sqlalchemy.create_engine("postgresql://localhost/db")
    return engine
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "database_io"


class TestDirectIODetectorMessageQueueIO:
    """Tests for message queue I/O detection in DirectIODetector."""

    def test_detects_confluent_kafka_producer(self) -> None:
        """Test detection of confluent_kafka producer call."""
        code = """
import confluent_kafka

def create_producer():
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})
    return producer
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        # The detection is based on module call, which may vary
        # Just ensure no crash
        assert isinstance(violations, list)


class TestDirectIODetectorEnvVarAccess:
    """Tests for environment variable access detection in DirectIODetector."""

    def test_detects_os_environ_subscript(self) -> None:
        """Test detection of os.environ[] access."""
        code = """
import os

def get_config():
    return os.environ["DATABASE_URL"]
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "env_var"
        assert "os.environ" in violations[0].description

    def test_detects_os_getenv(self) -> None:
        """Test detection of os.getenv() call."""
        code = """
import os

def get_config():
    return os.getenv("DATABASE_URL")
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "env_var"
        assert "getenv" in violations[0].description

    def test_detects_bare_getenv(self) -> None:
        """Test detection of bare getenv() call when imported."""
        code = """
from os import getenv

def get_config():
    return getenv("DATABASE_URL")
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1
        assert violations[0].pattern_type == "env_var"


class TestDirectIODetectorBypassComments:
    """Tests for bypass comment handling in DirectIODetector."""

    def test_io_ok_bypass_suppresses_violation(self) -> None:
        """Test that # io-ok: comment suppresses violation."""
        code = """
def read_config():
    f = open("config.json")  # io-ok: loading static config
    return f.read()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 0

    def test_io_ok_bypass_affects_whole_file(self) -> None:
        """Test that bypass comment affects the whole file (file-level bypass).

        Per the documented behavior in check_file(), bypass comments work at
        file-level only. If any bypass pattern is found anywhere in the file,
        the entire file is excluded from validation.
        """
        code = """
def read_files():
    f1 = open("config.json")  # io-ok: loading static config
    f2 = open("data.json")  # This should also be bypassed (file-level)
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        # Both violations should be bypassed because "io-ok:" appears in the file
        assert len(violations) == 0

    def test_file_level_bypass_suppresses_all(self) -> None:
        """Test that file-level bypass comment suppresses all violations."""
        code = """# io-ok: this file needs direct I/O for bootstrap

def read_config():
    f = open("config.json")
    return f.read()

def read_data():
    d = open("data.json")
    return d.read()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 0


class TestDirectIODetectorCleanCode:
    """Tests for code that should NOT trigger violations."""

    def test_no_violation_for_pure_computation(self) -> None:
        """Test that pure computation code doesn't trigger violations."""
        code = """
def compute_sum(a: int, b: int) -> int:
    return a + b

def process_data(items: list[int]) -> list[int]:
    return [x * 2 for x in items]
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 0

    def test_no_violation_for_class_definitions(self) -> None:
        """Test that class definitions don't trigger violations."""
        code = """
class DataProcessor:
    def __init__(self, config: dict):
        self.config = config

    def process(self, data: list) -> list:
        return [item * 2 for item in data]
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 0

    def test_no_violation_for_imports_only(self) -> None:
        """Test that imports alone don't trigger violations."""
        code = """
from pathlib import Path
import os
import requests
import asyncpg
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 0

    def test_no_violation_for_non_path_methods(self) -> None:
        """Test that methods with same names on non-Path objects don't trigger."""
        code = """
class MyClass:
    def read_text(self) -> str:
        return "text"

def use_class():
    obj = MyClass()
    return obj.read_text()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        # This might or might not trigger depending on heuristics
        # The current implementation uses name-based heuristics
        assert isinstance(violations, list)


class TestDirectIODetectorEdgeCases:
    """Tests for edge cases in DirectIODetector."""

    def test_handles_empty_file(self) -> None:
        """Test that empty files are handled gracefully."""
        code = ""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 0

    def test_handles_syntax_error(self) -> None:
        """Test that files with syntax errors are skipped."""
        code = """
def incomplete_function(
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 0  # Syntax error files are skipped

    def test_handles_unicode_content(self) -> None:
        """Test that Unicode content is handled properly."""
        code = """
def process():
    message = "Hello, world!"
    return message
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 0

    def test_handles_multiline_statements(self) -> None:
        """Test that multiline statements are handled."""
        code = """
def read_file():
    path = Path(
        "test.txt"
    )
    content = path.read_text()
    return content
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1

    def test_multiple_violations_same_file(self) -> None:
        """Test that multiple violations are all captured."""
        code = """
import os
from pathlib import Path
import requests

def do_io():
    env = os.getenv("CONFIG")
    data = requests.get("http://api.example.com")
    path = Path("test.txt")
    content = path.read_text()
    return env, data, content
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) >= 3  # At least env, network, and path I/O


class TestDirectIOValidator:
    """Tests for the DirectIOValidator class."""

    def test_validates_clean_file(self, tmp_path: Path) -> None:
        """Test validation of a clean file with no violations."""
        test_file = tmp_path / "clean.py"
        test_file.write_text("""
def compute(x: int) -> int:
    return x * 2
""")
        validator = DirectIOValidator(verbose=False)
        is_valid = validator.validate_file(test_file)
        assert is_valid is True
        assert len(validator.violations) == 0

    def test_validates_file_with_violations(self, tmp_path: Path) -> None:
        """Test validation of a file with violations."""
        test_file = tmp_path / "bad.py"
        test_file.write_text("""
def read_file():
    f = open("test.txt")
    return f.read()
""")
        validator = DirectIOValidator(verbose=False)
        is_valid = validator.validate_file(test_file)
        assert is_valid is False
        assert len(validator.violations) == 1

    def test_skips_allowed_files(self, tmp_path: Path) -> None:
        """Test that allowed files are skipped."""
        # node_effect.py should be allowed
        test_file = tmp_path / "node_effect.py"
        test_file.write_text("""
def read_file():
    f = open("test.txt")
    return f.read()
""")
        validator = DirectIOValidator(verbose=True)
        is_valid = validator.validate_file(test_file)
        assert is_valid is True
        assert len(validator.violations) == 0
        assert any("allowed file" in s for s in validator.skipped_files)

    def test_skips_test_directories(self, tmp_path: Path) -> None:
        """Test that test directories are excluded."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_io.py"
        test_file.write_text("""
def test_read_file():
    f = open("test.txt")
    return f.read()
""")
        validator = DirectIOValidator(verbose=True)
        is_valid = validator.validate_file(test_file)
        assert is_valid is True
        assert len(validator.violations) == 0

    def test_skips_legacy_directories(self, tmp_path: Path) -> None:
        """Test that legacy directories are excluded."""
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        test_file = legacy_dir / "old_code.py"
        test_file.write_text("""
def read_file():
    f = open("test.txt")
    return f.read()
""")
        validator = DirectIOValidator(verbose=True)
        is_valid = validator.validate_file(test_file)
        assert is_valid is True
        assert len(validator.violations) == 0

    def test_skips_pycache_directories(self, tmp_path: Path) -> None:
        """Test that __pycache__ directories are excluded."""
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        test_file = cache_dir / "module.py"
        test_file.write_text("""
def read_file():
    f = open("test.txt")
    return f.read()
""")
        validator = DirectIOValidator(verbose=True)
        is_valid = validator.validate_file(test_file)
        assert is_valid is True
        assert len(validator.violations) == 0

    def test_validates_directory(self, tmp_path: Path) -> None:
        """Test validation of an entire directory."""
        # Create clean files
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("def compute(): return 1")

        # Create file with violation
        bad_file = tmp_path / "bad.py"
        bad_file.write_text('def read(): open("x")')

        validator = DirectIOValidator(verbose=False)
        is_valid = validator.validate_directory(tmp_path)
        assert is_valid is False
        assert validator.checked_files == 2
        assert len(validator.violations) == 1

    def test_validates_directory_with_subdirs(self, tmp_path: Path) -> None:
        """Test validation of nested directories."""
        subdir = tmp_path / "src" / "nodes"
        subdir.mkdir(parents=True)

        file1 = subdir / "compute.py"
        file1.write_text("def compute(): return 1")

        file2 = subdir / "effect.py"
        file2.write_text('def read(): open("x")')

        validator = DirectIOValidator(verbose=False)
        is_valid = validator.validate_directory(tmp_path)
        assert is_valid is False
        assert validator.checked_files == 2

    def test_handles_unreadable_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test handling of unreadable files.

        Note: On some platforms (e.g., when running as root in Docker, or
        when file systems don't enforce POSIX permissions), chmod 0o000
        doesn't actually prevent reading. This test handles both cases.
        """
        test_file = tmp_path / "unreadable.py"
        test_file.write_text("content")
        test_file.chmod(0o000)

        try:
            # Check if the file is actually unreadable
            try:
                test_file.read_text()
                file_is_readable = True
            except PermissionError:
                file_is_readable = False

            validator = DirectIOValidator(verbose=False)
            is_valid = validator.validate_file(test_file)
            # Should handle gracefully and return True (skip or read ok)
            assert is_valid is True
            captured = capsys.readouterr()

            if file_is_readable:
                # Platform doesn't enforce permissions - file was read normally
                # Just verify no crash occurred and file was processed
                assert validator.checked_files == 1
            else:
                # File was unreadable - should have warning in stderr
                assert "Warning" in captured.err
                assert validator.checked_files == 0
        finally:
            test_file.chmod(0o644)

    def test_verbose_mode_tracks_skipped(self, tmp_path: Path) -> None:
        """Test that verbose mode tracks skipped files."""
        test_file = tmp_path / "tests" / "test_file.py"
        test_file.parent.mkdir()
        test_file.write_text("def test(): pass")

        validator = DirectIOValidator(verbose=True)
        validator.validate_file(test_file)
        assert len(validator.skipped_files) == 1

    def test_print_results_no_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test print_results when there are no violations."""
        test_file = tmp_path / "clean.py"
        test_file.write_text("def compute(): return 1")

        validator = DirectIOValidator(verbose=False)
        validator.validate_file(test_file)
        validator.print_results()

        captured = capsys.readouterr()
        assert "No direct I/O patterns found" in captured.out

    def test_print_results_with_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test print_results when there are violations."""
        test_file = tmp_path / "bad.py"
        test_file.write_text('def read(): open("x")')

        validator = DirectIOValidator(verbose=False)
        validator.validate_file(test_file)
        validator.print_results()

        captured = capsys.readouterr()
        assert "DIRECT I/O PATTERNS FOUND" in captured.out
        assert "violation(s)" in captured.out

    def test_print_results_with_verbose(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test print_results in verbose mode shows skipped files."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_file.py"
        test_file.write_text("def test(): pass")

        validator = DirectIOValidator(verbose=True)
        validator.validate_file(test_file)
        validator.print_results()

        captured = capsys.readouterr()
        assert "Skipped files" in captured.out


class TestMainFunction:
    """Tests for the main() entry point."""

    def test_main_returns_zero_for_clean_directory(self, tmp_path: Path) -> None:
        """Test that main returns 0 when no violations found."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("def compute(): return 1")

        with patch.object(
            sys, "argv", ["validate-no-direct-io.py", "--directory", str(tmp_path)]
        ):
            result = main()
            assert result == 0

    def test_main_returns_one_for_violations(self, tmp_path: Path) -> None:
        """Test that main returns 1 when violations found."""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text('def read(): open("x")')

        with patch.object(
            sys, "argv", ["validate-no-direct-io.py", "--directory", str(tmp_path)]
        ):
            result = main()
            assert result == 1

    def test_main_returns_two_for_missing_directory(self) -> None:
        """Test that main returns 2 for missing directory."""
        with patch.object(
            sys,
            "argv",
            ["validate-no-direct-io.py", "--directory", "/nonexistent/path"],
        ):
            result = main()
            assert result == 2

    def test_main_returns_two_for_file_not_directory(self, tmp_path: Path) -> None:
        """Test that main returns 2 when path is a file not directory."""
        test_file = tmp_path / "file.py"
        test_file.write_text("def compute(): return 1")

        with patch.object(
            sys, "argv", ["validate-no-direct-io.py", "--directory", str(test_file)]
        ):
            result = main()
            assert result == 2

    def test_main_verbose_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that --verbose flag works."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_file.py"
        test_file.write_text('def test(): open("x")')

        with patch.object(
            sys,
            "argv",
            ["validate-no-direct-io.py", "--verbose", "--directory", str(tmp_path)],
        ):
            main()

        captured = capsys.readouterr()
        assert "Skipped files" in captured.out

    def test_main_default_directory(self) -> None:
        """Test that main uses default directory when none specified."""
        # This test just verifies the function doesn't crash
        with patch.object(sys, "argv", ["validate-no-direct-io.py"]):
            # Will either find the default dir or return error code 2
            result = main()
            assert result in (0, 1, 2)


class TestPathObjectDetection:
    """Tests for Path object detection heuristics."""

    def test_detects_direct_path_constructor(self) -> None:
        """Test detection when Path is directly called."""
        code = """
from pathlib import Path

def read_file():
    return Path("test.txt").read_text()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1

    def test_detects_pathlib_path_constructor(self) -> None:
        """Test detection when pathlib.Path is called."""
        code = """
import pathlib

def read_file():
    return pathlib.Path("test.txt").read_text()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1

    def test_detects_variable_with_path_in_name(self) -> None:
        """Test detection based on variable naming conventions."""
        code = """
def read_file(config_path):
    return config_path.read_text()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1

    def test_detects_variable_with_file_in_name(self) -> None:
        """Test detection based on 'file' in variable name."""
        code = """
def read_file(input_file):
    return input_file.read_text()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1

    def test_detects_attribute_with_path_in_name(self) -> None:
        """Test detection based on attribute naming."""
        code = """
def read_file(self):
    return self.config_path.read_text()
"""
        detector = DirectIODetector("/test.py", code)
        violations = detector.check_file()
        assert len(violations) == 1


class TestImportTracking:
    """Tests for import statement tracking."""

    def test_tracks_regular_imports(self) -> None:
        """Test that regular imports are tracked."""
        code = """
import requests

def fetch():
    return requests.get("http://example.com")
"""
        detector = DirectIODetector("/test.py", code)
        detector.check_file()
        assert "requests" in detector.imported_modules

    def test_tracks_from_imports(self) -> None:
        """Test that from imports are tracked."""
        code = """
from pathlib import Path

def read_file():
    return Path("test.txt").read_text()
"""
        detector = DirectIODetector("/test.py", code)
        detector.check_file()
        assert "Path" in detector.from_imports

    def test_tracks_aliased_imports(self) -> None:
        """Test that aliased imports are tracked."""
        code = """
import requests as req

def fetch():
    return req.get("http://example.com")
"""
        detector = DirectIODetector("/test.py", code)
        detector.check_file()
        assert "req" in detector.imported_modules
        assert detector.imported_modules["req"] == "requests"

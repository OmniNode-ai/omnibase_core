"""
Comprehensive tests for the AST-based transport import validator.

Tests cover:
- TransportImportChecker AST visitor
- check_file function
- iter_python_files function
- Banned import detection (aiohttp, httpx, requests, kafka, redis, etc.)
- TYPE_CHECKING guarded imports (allowed per ADR-005)
- Aliased typing imports (`import typing as t` then `if t.TYPE_CHECKING:`)
- Aliased TYPE_CHECKING imports (`from typing import TYPE_CHECKING as TC`)
- File processing errors (SyntaxError, UnicodeDecodeError, etc.)
- Exclusion logic
- Directory traversal skipping

Linear ticket: OMN-1039
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Import the validation script components via importlib
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
scripts_dir = str(SCRIPTS_DIR)
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# Module-level variables populated when the script loads
_module_loaded = False
Violation: Any = None
FileProcessingError: Any = None
TransportImportChecker: Any = None
check_file: Any = None
iter_python_files: Any = None
main: Any = None
BANNED_MODULES: Any = None
SKIP_DIRECTORIES: Any = None


def _load_module() -> bool:
    """Load the validate_no_transport_imports module.

    Returns:
        True if module loaded successfully, False otherwise.
    """
    global _module_loaded, Violation, FileProcessingError, TransportImportChecker
    global check_file, iter_python_files, main, BANNED_MODULES, SKIP_DIRECTORIES

    if _module_loaded:
        return True

    script_path = SCRIPTS_DIR / "validate_no_transport_imports.py"
    if not script_path.exists():
        return False

    spec = importlib.util.spec_from_file_location(
        "validate_no_transport_imports", script_path
    )
    if spec is None:
        return False
    if spec.loader is None:
        return False

    _module = importlib.util.module_from_spec(spec)
    # Add to sys.modules before exec to avoid dataclass issues
    sys.modules["validate_no_transport_imports"] = _module
    spec.loader.exec_module(_module)

    # Extract classes and functions from the loaded module
    Violation = _module.Violation
    FileProcessingError = _module.FileProcessingError
    TransportImportChecker = _module.TransportImportChecker
    check_file = _module.check_file
    iter_python_files = _module.iter_python_files
    main = _module.main
    BANNED_MODULES = _module.BANNED_MODULES
    SKIP_DIRECTORIES = _module.SKIP_DIRECTORIES

    _module_loaded = True
    return True


def skip_if_module_not_loaded() -> None:
    """Skip test if the module is not available."""
    if not _load_module():
        pytest.skip("Script not found: scripts/validate_no_transport_imports.py")


# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]


@pytest.mark.unit
class TestViolationDataclass:
    """Tests for Violation dataclass creation and formatting."""

    def test_violation_creation(self) -> None:
        """Test that Violation can be created with all fields."""
        skip_if_module_not_loaded()

        violation = Violation(
            file_path=Path("/test/file.py"),
            line_number=10,
            module_name="kafka",
            import_statement="import kafka",
        )
        assert violation.file_path == Path("/test/file.py")
        assert violation.line_number == 10
        assert violation.module_name == "kafka"
        assert violation.import_statement == "import kafka"

    def test_violation_str_format(self) -> None:
        """Test violation __str__ method."""
        skip_if_module_not_loaded()

        violation = Violation(
            file_path=Path("/test/file.py"),
            line_number=10,
            module_name="kafka",
            import_statement="import kafka",
        )
        formatted = str(violation)
        assert "file.py" in formatted
        assert "10" in formatted
        assert "kafka" in formatted


@pytest.mark.unit
class TestFileProcessingErrorDataclass:
    """Tests for FileProcessingError dataclass."""

    def test_error_creation(self) -> None:
        """Test that FileProcessingError can be created with all fields."""
        skip_if_module_not_loaded()

        error = FileProcessingError(
            file_path=Path("/test/file.py"),
            error_type="SyntaxError",
            error_message="Invalid syntax at line 5",
        )
        assert error.file_path == Path("/test/file.py")
        assert error.error_type == "SyntaxError"
        assert error.error_message == "Invalid syntax at line 5"

    def test_error_str_format(self) -> None:
        """Test FileProcessingError __str__ method."""
        skip_if_module_not_loaded()

        error = FileProcessingError(
            file_path=Path("/test/file.py"),
            error_type="SyntaxError",
            error_message="Invalid syntax",
        )
        formatted = str(error)
        assert "file.py" in formatted
        assert "SyntaxError" in formatted


@pytest.mark.unit
class TestBannedModulesConfiguration:
    """Tests that banned modules configuration is complete."""

    def test_banned_modules_contains_http_clients(self) -> None:
        """Test that HTTP client modules are in the banned list."""
        skip_if_module_not_loaded()
        assert "aiohttp" in BANNED_MODULES
        assert "httpx" in BANNED_MODULES
        assert "requests" in BANNED_MODULES
        assert "urllib3" in BANNED_MODULES

    def test_banned_modules_contains_kafka_clients(self) -> None:
        """Test that Kafka client modules are in the banned list."""
        skip_if_module_not_loaded()
        assert "kafka" in BANNED_MODULES
        assert "aiokafka" in BANNED_MODULES
        assert "confluent_kafka" in BANNED_MODULES

    def test_banned_modules_contains_redis_clients(self) -> None:
        """Test that Redis client modules are in the banned list."""
        skip_if_module_not_loaded()
        assert "redis" in BANNED_MODULES
        assert "aioredis" in BANNED_MODULES

    def test_banned_modules_contains_database_clients(self) -> None:
        """Test that database client modules are in the banned list."""
        skip_if_module_not_loaded()
        assert "asyncpg" in BANNED_MODULES
        assert "psycopg2" in BANNED_MODULES
        assert "psycopg" in BANNED_MODULES
        assert "aiomysql" in BANNED_MODULES

    def test_banned_modules_contains_mq_clients(self) -> None:
        """Test that message queue modules are in the banned list."""
        skip_if_module_not_loaded()
        assert "pika" in BANNED_MODULES
        assert "aio_pika" in BANNED_MODULES
        assert "kombu" in BANNED_MODULES
        assert "celery" in BANNED_MODULES

    def test_banned_modules_contains_grpc(self) -> None:
        """Test that gRPC module is in the banned list."""
        skip_if_module_not_loaded()
        assert "grpc" in BANNED_MODULES

    def test_banned_modules_contains_websocket(self) -> None:
        """Test that WebSocket modules are in the banned list."""
        skip_if_module_not_loaded()
        assert "websockets" in BANNED_MODULES
        assert "wsproto" in BANNED_MODULES


@pytest.mark.unit
class TestBannedImportDetection:
    """Tests detection of banned transport library imports."""

    def test_detects_import_kafka(self) -> None:
        """Test detection of 'import kafka'."""
        skip_if_module_not_loaded()

        code = """
import kafka
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "kafka"

    def test_detects_from_kafka_import(self) -> None:
        """Test detection of 'from kafka import ...'."""
        skip_if_module_not_loaded()

        code = """
from kafka import KafkaProducer
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "kafka"

    def test_detects_import_httpx(self) -> None:
        """Test detection of 'import httpx'."""
        skip_if_module_not_loaded()

        code = """
import httpx
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "httpx"

    def test_detects_from_aiohttp_import(self) -> None:
        """Test detection of 'from aiohttp import ClientSession'."""
        skip_if_module_not_loaded()

        code = """
from aiohttp import ClientSession
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "aiohttp"

    def test_detects_import_redis(self) -> None:
        """Test detection of 'import redis'."""
        skip_if_module_not_loaded()

        code = """
import redis
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "redis"

    def test_detects_import_asyncpg(self) -> None:
        """Test detection of 'import asyncpg'."""
        skip_if_module_not_loaded()

        code = """
import asyncpg
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "asyncpg"

    def test_detects_submodule_import(self) -> None:
        """Test detection of 'from kafka.errors import KafkaError'."""
        skip_if_module_not_loaded()

        code = """
from kafka.errors import KafkaError
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "kafka"

    def test_detects_dotted_import(self) -> None:
        """Test detection of 'import redis.asyncio'."""
        skip_if_module_not_loaded()

        code = """
import redis.asyncio
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "redis"

    def test_detects_aliased_import(self) -> None:
        """Test detection of 'import kafka as k'."""
        skip_if_module_not_loaded()

        code = """
import kafka as k
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "kafka"

    def test_detects_multiple_violations(self) -> None:
        """Test that multiple violations are detected."""
        skip_if_module_not_loaded()

        code = """
import kafka
import redis
from httpx import Client
from asyncpg import connect
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 4


@pytest.mark.unit
class TestTypeCheckingBlockHandling:
    """Tests that TYPE_CHECKING block imports are allowed."""

    def test_allows_imports_in_type_checking_block(self) -> None:
        """Test that imports inside TYPE_CHECKING blocks are allowed."""
        skip_if_module_not_loaded()

        code = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import kafka
    from redis import Redis
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_typing_dot_type_checking_block(self) -> None:
        """Test that typing.TYPE_CHECKING blocks are recognized."""
        skip_if_module_not_loaded()

        code = """
import typing

if typing.TYPE_CHECKING:
    import httpx
    from aiohttp import ClientSession
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_aliased_typing_type_checking_block(self) -> None:
        """Test that aliased typing.TYPE_CHECKING blocks are recognized.

        Pattern: import typing as t; if t.TYPE_CHECKING:
        """
        skip_if_module_not_loaded()

        code = """
import typing as t

if t.TYPE_CHECKING:
    import kafka
    from redis import Redis
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_tp_aliased_type_checking_block(self) -> None:
        """Test that 'import typing as tp' aliased TYPE_CHECKING blocks work."""
        skip_if_module_not_loaded()

        code = """
import typing as tp

if tp.TYPE_CHECKING:
    import kafka
    from redis import Redis
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_aliased_type_checking_constant(self) -> None:
        """Test that aliased TYPE_CHECKING constant is recognized.

        Pattern: from typing import TYPE_CHECKING as TC; if TC:
        """
        skip_if_module_not_loaded()

        code = """
from typing import TYPE_CHECKING as TC

if TC:
    import kafka
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        # This SHOULD be allowed - aliased TYPE_CHECKING constant
        assert len(checker.violations) == 0

    def test_allows_nested_conditions_in_type_checking(self) -> None:
        """Test nested conditions inside TYPE_CHECKING blocks."""
        skip_if_module_not_loaded()

        code = """
from typing import TYPE_CHECKING
import sys

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        import kafka
    else:
        from kafka import KafkaProducer
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_detects_imports_outside_type_checking(self) -> None:
        """Test that imports outside TYPE_CHECKING are still detected."""
        skip_if_module_not_loaded()

        code = """
from typing import TYPE_CHECKING

import kafka  # This should be detected

if TYPE_CHECKING:
    import redis  # This should be allowed
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "kafka"


@pytest.mark.unit
class TestAllowedImports:
    """Tests that allowed imports pass validation."""

    def test_allows_typing_import(self) -> None:
        """Test that typing imports are allowed."""
        skip_if_module_not_loaded()

        code = """
import typing
from typing import Optional, List
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_pydantic_import(self) -> None:
        """Test that pydantic imports are allowed."""
        skip_if_module_not_loaded()

        code = """
from pydantic import BaseModel
import pydantic
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_standard_library_imports(self) -> None:
        """Test that standard library imports are allowed."""
        skip_if_module_not_loaded()

        code = """
import os
import sys
import json
import pathlib
from collections import defaultdict
from dataclasses import dataclass
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0


@pytest.mark.unit
class TestCheckFileFunction:
    """Tests for the check_file() function."""

    def test_check_clean_file(self, tmp_path: Path) -> None:
        """Test checking a clean file with no banned imports."""
        skip_if_module_not_loaded()

        test_file = tmp_path / "clean.py"
        test_file.write_text("""
import os
from typing import Optional
""")

        violations, errors = check_file(test_file)

        assert len(violations) == 0
        assert len(errors) == 0

    def test_check_file_with_violations(self, tmp_path: Path) -> None:
        """Test checking a file with banned imports."""
        skip_if_module_not_loaded()

        test_file = tmp_path / "bad.py"
        test_file.write_text("""
import kafka
from redis import Redis
""")

        violations, errors = check_file(test_file)

        assert len(violations) == 2
        assert len(errors) == 0

    def test_check_empty_file(self, tmp_path: Path) -> None:
        """Test checking an empty file."""
        skip_if_module_not_loaded()

        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        violations, errors = check_file(test_file)

        assert len(violations) == 0
        assert len(errors) == 0

    def test_check_file_syntax_error(self, tmp_path: Path) -> None:
        """Test that files with syntax errors are handled gracefully."""
        skip_if_module_not_loaded()

        test_file = tmp_path / "syntax_error.py"
        test_file.write_text("""
def incomplete(
""")

        violations, errors = check_file(test_file)

        assert len(violations) == 0
        assert len(errors) == 1
        assert errors[0].error_type == "SyntaxError"

    def test_check_file_unicode_error(self, tmp_path: Path) -> None:
        """Test that files with encoding errors are handled gracefully."""
        skip_if_module_not_loaded()

        test_file = tmp_path / "encoding_error.py"
        test_file.write_bytes(b"\xff\xfe invalid utf-8 \x80\x81")

        violations, errors = check_file(test_file)

        assert len(violations) == 0
        assert len(errors) == 1
        assert errors[0].error_type == "UnicodeDecodeError"

    def test_check_file_type_checking_guarded(self, tmp_path: Path) -> None:
        """Test that TYPE_CHECKING guarded imports are allowed in files."""
        skip_if_module_not_loaded()

        test_file = tmp_path / "guarded.py"
        test_file.write_text("""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import kafka
    from httpx import Client
""")

        violations, errors = check_file(test_file)

        assert len(violations) == 0
        assert len(errors) == 0


@pytest.mark.unit
class TestIterPythonFilesFunction:
    """Tests for the iter_python_files() function."""

    def test_finds_python_files(self, tmp_path: Path) -> None:
        """Test finding Python files in a directory."""
        skip_if_module_not_loaded()

        (tmp_path / "file1.py").write_text("import os")
        (tmp_path / "file2.py").write_text("import sys")
        (tmp_path / "file.txt").write_text("not python")

        files = list(iter_python_files(tmp_path, set()))

        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def test_skips_pycache_directories(self, tmp_path: Path) -> None:
        """Test that __pycache__ directories are skipped."""
        skip_if_module_not_loaded()

        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("import kafka")
        (tmp_path / "main.py").write_text("import sys")

        files = list(iter_python_files(tmp_path, set()))

        assert len(files) == 1
        assert files[0].name == "main.py"

    def test_skips_venv_directories(self, tmp_path: Path) -> None:
        """Test that .venv and venv directories are skipped."""
        skip_if_module_not_loaded()

        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "site.py").write_text("import kafka")

        venv2 = tmp_path / "venv"
        venv2.mkdir()
        (venv2 / "site.py").write_text("import redis")

        (tmp_path / "main.py").write_text("import sys")

        files = list(iter_python_files(tmp_path, set()))

        assert len(files) == 1
        assert files[0].name == "main.py"

    def test_skips_excluded_paths(self, tmp_path: Path) -> None:
        """Test that user-provided exclusions are respected."""
        skip_if_module_not_loaded()

        (tmp_path / "include.py").write_text("import os")
        (tmp_path / "exclude.py").write_text("import kafka")

        exclude_path = tmp_path / "exclude.py"
        files = list(iter_python_files(tmp_path, {exclude_path}))

        assert len(files) == 1
        assert files[0].name == "include.py"

    def test_skips_common_cache_directories(self, tmp_path: Path) -> None:
        """Test that common cache directories are skipped."""
        skip_if_module_not_loaded()

        cache_dirs = [".git", ".pytest_cache", ".mypy_cache", ".ruff_cache"]
        for cache_dir in cache_dirs:
            cache = tmp_path / cache_dir
            cache.mkdir()
            (cache / "module.py").write_text("import kafka")

        (tmp_path / "main.py").write_text("import sys")

        files = list(iter_python_files(tmp_path, set()))

        assert len(files) == 1
        assert files[0].name == "main.py"

    def test_finds_nested_python_files(self, tmp_path: Path) -> None:
        """Test that Python files in nested directories are found."""
        skip_if_module_not_loaded()

        subdir = tmp_path / "src" / "module"
        subdir.mkdir(parents=True)
        (subdir / "nested.py").write_text("import os")
        (tmp_path / "main.py").write_text("import sys")

        files = list(iter_python_files(tmp_path, set()))

        assert len(files) == 2


@pytest.mark.unit
class TestMainFunction:
    """Tests for the main() entry point."""

    def test_returns_zero_for_clean_files(self, tmp_path: Path) -> None:
        """Test that main returns 0 when no violations found."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "clean.py").write_text("import os")

        with patch.object(
            sys,
            "argv",
            ["validate_no_transport_imports.py", "--src-dir", str(test_dir)],
        ):
            result = main()
            assert result == 0

    def test_returns_one_for_violations(self, tmp_path: Path) -> None:
        """Test that main returns 1 when violations found."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "bad.py").write_text("import kafka")

        with patch.object(
            sys,
            "argv",
            ["validate_no_transport_imports.py", "--src-dir", str(test_dir)],
        ):
            result = main()
            assert result == 1

    def test_returns_one_for_nonexistent_directory(self) -> None:
        """Test that main returns 1 for nonexistent source directory."""
        skip_if_module_not_loaded()

        with patch.object(
            sys,
            "argv",
            ["validate_no_transport_imports.py", "--src-dir", "/nonexistent/path"],
        ):
            result = main()
            assert result == 1

    def test_exclude_flag_works(self, tmp_path: Path) -> None:
        """Test that --exclude flag excludes files from validation."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src"
        test_dir.mkdir()
        clean_file = test_dir / "clean.py"
        clean_file.write_text("import os")
        bad_file = test_dir / "bad.py"
        bad_file.write_text("import kafka")

        with patch.object(
            sys,
            "argv",
            [
                "validate_no_transport_imports.py",
                "--src-dir",
                str(test_dir),
                "--exclude",
                str(bad_file),
            ],
        ):
            result = main()
            assert result == 0

    def test_verbose_flag_shows_snippets(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that --verbose flag shows import statement snippets."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "bad.py").write_text("import kafka")

        with patch.object(
            sys,
            "argv",
            [
                "validate_no_transport_imports.py",
                "--verbose",
                "--src-dir",
                str(test_dir),
            ],
        ):
            main()

        captured = capsys.readouterr()
        assert "kafka" in captured.out


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_nested_imports_in_functions(self) -> None:
        """Test that imports nested inside functions are detected."""
        skip_if_module_not_loaded()

        code = """
def some_function():
    import kafka
    return kafka.KafkaProducer()
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1

    def test_handles_nested_imports_in_classes(self) -> None:
        """Test that imports nested inside classes are detected."""
        skip_if_module_not_loaded()

        code = """
class MyClass:
    def __init__(self):
        import redis
        self.client = redis.Redis()
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1

    def test_string_containing_import_passes(self) -> None:
        """Test that strings containing import names don't trigger violations."""
        skip_if_module_not_loaded()

        code = '''
message = "connect to redis server"
doc = """
This module uses redis for caching.
import redis  # This is just documentation
"""
'''
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_comments_containing_imports_pass(self) -> None:
        """Test that comments with import names don't trigger violations."""
        skip_if_module_not_loaded()

        code = """
# import kafka  - we used to use this
# from redis import Redis
# TODO: consider using httpx
import typing
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_try_except_imports_detected(self) -> None:
        """Test that imports in try/except blocks are detected."""
        skip_if_module_not_loaded()

        code = """
try:
    import redis
except ImportError:
    redis = None
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1

    def test_captures_correct_line_numbers(self) -> None:
        """Test that line numbers are correctly captured."""
        skip_if_module_not_loaded()

        code = """

import kafka

import redis
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 2
        line_numbers = {v.line_number for v in checker.violations}
        assert 3 in line_numbers  # import kafka
        assert 5 in line_numbers  # import redis

    def test_relative_imports_not_flagged(self) -> None:
        """Test that relative imports without module are handled."""
        skip_if_module_not_loaded()

        code = """
from . import models
from .. import utils
"""
        tree = ast.parse(code)
        checker = TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0


@pytest.mark.unit
class TestSkipDirectoriesConfiguration:
    """Tests for SKIP_DIRECTORIES configuration."""

    def test_skip_directories_contains_common_excludes(self) -> None:
        """Test that common excluded directories are configured."""
        skip_if_module_not_loaded()

        expected = [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            ".pytest_cache",
            ".mypy_cache",
        ]
        for dir_name in expected:
            assert dir_name in SKIP_DIRECTORIES

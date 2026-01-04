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
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Protocol, runtime_checkable
from unittest.mock import patch

import pytest

# Path to the scripts directory - computed at module load time
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"


# Protocol definitions for dynamically loaded types
# These define the expected interface of types loaded from validate_no_transport_imports.py


@runtime_checkable
class ProtocolViolation(Protocol):
    """Protocol for the Violation dataclass from the validator script."""

    file_path: Path
    line_number: int
    module_name: str
    import_statement: str


@runtime_checkable
class ProtocolFileProcessingError(Protocol):
    """Protocol for the FileProcessingError dataclass from the validator script."""

    file_path: Path
    error_type: str
    error_message: str


@runtime_checkable
class ProtocolTransportImportChecker(Protocol):
    """Protocol for the TransportImportChecker class from the validator script."""

    violations: list[ProtocolViolation]

    def visit(self, node: ast.AST) -> None:
        """Visit an AST node."""
        ...


# Type aliases for constructor callables
# These define the expected signature for creating instances of the dynamically loaded types
ViolationConstructor = Callable[..., ProtocolViolation]
FileProcessingErrorConstructor = Callable[..., ProtocolFileProcessingError]
TransportImportCheckerConstructor = Callable[[str], ProtocolTransportImportChecker]


@dataclass(frozen=True)
class TransportValidatorModule:
    """Container for dynamically loaded transport validator components.

    This dataclass provides typed access to components loaded from the
    validate_no_transport_imports.py script. Protocol classes define the
    expected interfaces for the dynamically loaded types, enabling type-safe
    access without using Any.

    Type Annotations:
        - Constructor types use Protocol-based Callable signatures to define
          the expected interface of instances created by the constructors.
        - Function signatures use Callable with accurate parameter types.
        - Constants use their actual types (frozenset[str]).

    Thread Safety:
        Instances are immutable (frozen=True) and safe to share across threads.
        The underlying module components may have their own thread safety
        constraints (see TransportImportChecker documentation).
    """

    # Constructor types - return Protocol-defined interfaces
    # These are callable factories that create instances matching the Protocol interfaces
    Violation: ViolationConstructor
    FileProcessingError: FileProcessingErrorConstructor
    TransportImportChecker: TransportImportCheckerConstructor

    # Function signatures with accurate types
    check_file: Callable[
        [Path], tuple[list[ProtocolViolation], list[ProtocolFileProcessingError]]
    ]
    iter_python_files: Callable[[Path, set[Path]], Iterator[Path]]
    main: Callable[[], int]

    # Constants with accurate types from the script
    BANNED_MODULES: frozenset[str]
    SKIP_DIRECTORIES: frozenset[str]


# Thread-safe module loading for parallel test execution (pytest-xdist)
_module_cache_lock = threading.Lock()
_cached_module: TransportValidatorModule | None = None


def _load_module() -> TransportValidatorModule | None:
    """Load the validate_no_transport_imports module safely.

    This function uses importlib.util to load the script without modifying
    sys.path globally, making it safe for parallel test execution with
    pytest-xdist.

    Returns:
        TransportValidatorModule with all components if successful, None otherwise.

    Thread Safety:
        Uses a lock to ensure the module is only loaded once even when called
        from multiple threads concurrently.
    """
    global _cached_module

    # Fast path: check if already loaded
    if _cached_module is not None:
        return _cached_module

    with _module_cache_lock:
        # Double-check after acquiring lock (thread-safety pattern)
        # mypy doesn't understand that _cached_module could change between
        # the first check and acquiring the lock due to another thread
        if _cached_module is not None:
            return _cached_module  # type: ignore[unreachable]

        script_path = SCRIPTS_DIR / "validate_no_transport_imports.py"
        if not script_path.exists():
            return None

        spec = importlib.util.spec_from_file_location(
            "validate_no_transport_imports", script_path
        )
        if spec is None or spec.loader is None:
            return None

        module: ModuleType = importlib.util.module_from_spec(spec)
        # Add to sys.modules before exec to avoid dataclass issues
        sys.modules["validate_no_transport_imports"] = module
        spec.loader.exec_module(module)

        # Extract and wrap components in typed container
        # The module attributes are cast to our Protocol-based types
        _cached_module = TransportValidatorModule(
            Violation=module.Violation,
            FileProcessingError=module.FileProcessingError,
            TransportImportChecker=module.TransportImportChecker,
            check_file=module.check_file,
            iter_python_files=module.iter_python_files,
            main=module.main,
            BANNED_MODULES=module.BANNED_MODULES,
            SKIP_DIRECTORIES=module.SKIP_DIRECTORIES,
        )
        return _cached_module


@pytest.fixture(scope="module")
def validator() -> TransportValidatorModule:
    """Pytest fixture providing access to transport validator components.

    This fixture loads the validate_no_transport_imports.py script and provides
    typed access to all its components. Tests that need access to the validator
    should use this fixture instead of loading the module directly.

    The fixture is module-scoped for performance - the script is loaded once
    per test module rather than once per test.

    Returns:
        TransportValidatorModule containing all loaded components.

    Raises:
        pytest.skip: If the script cannot be found or loaded.

    Example:
        def test_something(validator: TransportValidatorModule) -> None:
            violation = validator.Violation(
                file_path=Path("/test.py"),
                line_number=1,
                module_name="kafka",
                import_statement="import kafka",
            )
            assert violation.module_name == "kafka"
    """
    module = _load_module()
    if module is None:
        pytest.skip("Script not found: scripts/validate_no_transport_imports.py")
    return module


# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]


class TestViolationDataclass:
    """Tests for Violation dataclass creation and formatting."""

    def test_violation_creation(self, validator: TransportValidatorModule) -> None:
        """Test that Violation can be created with all fields."""
        violation = validator.Violation(
            file_path=Path("/test/file.py"),
            line_number=10,
            module_name="kafka",
            import_statement="import kafka",
        )
        assert violation.file_path == Path("/test/file.py")
        assert violation.line_number == 10
        assert violation.module_name == "kafka"
        assert violation.import_statement == "import kafka"

    def test_violation_str_format(self, validator: TransportValidatorModule) -> None:
        """Test violation __str__ method."""
        violation = validator.Violation(
            file_path=Path("/test/file.py"),
            line_number=10,
            module_name="kafka",
            import_statement="import kafka",
        )
        formatted = str(violation)
        assert "file.py" in formatted
        assert "10" in formatted
        assert "kafka" in formatted


class TestFileProcessingErrorDataclass:
    """Tests for FileProcessingError dataclass."""

    def test_error_creation(self, validator: TransportValidatorModule) -> None:
        """Test that FileProcessingError can be created with all fields."""
        error = validator.FileProcessingError(
            file_path=Path("/test/file.py"),
            error_type="SyntaxError",
            error_message="Invalid syntax at line 5",
        )
        assert error.file_path == Path("/test/file.py")
        assert error.error_type == "SyntaxError"
        assert error.error_message == "Invalid syntax at line 5"

    def test_error_str_format(self, validator: TransportValidatorModule) -> None:
        """Test FileProcessingError __str__ method."""
        error = validator.FileProcessingError(
            file_path=Path("/test/file.py"),
            error_type="SyntaxError",
            error_message="Invalid syntax",
        )
        formatted = str(error)
        assert "file.py" in formatted
        assert "SyntaxError" in formatted


class TestBannedModulesConfiguration:
    """Tests that banned modules configuration is complete."""

    def test_banned_modules_contains_http_clients(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that HTTP client modules are in the banned list."""
        assert "aiohttp" in validator.BANNED_MODULES
        assert "httpx" in validator.BANNED_MODULES
        assert "requests" in validator.BANNED_MODULES
        assert "urllib3" in validator.BANNED_MODULES

    def test_banned_modules_contains_kafka_clients(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that Kafka client modules are in the banned list."""
        assert "kafka" in validator.BANNED_MODULES
        assert "aiokafka" in validator.BANNED_MODULES
        assert "confluent_kafka" in validator.BANNED_MODULES

    def test_banned_modules_contains_redis_clients(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that Redis client modules are in the banned list."""
        assert "redis" in validator.BANNED_MODULES
        assert "aioredis" in validator.BANNED_MODULES

    def test_banned_modules_contains_database_clients(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that database client modules are in the banned list."""
        assert "asyncpg" in validator.BANNED_MODULES
        assert "psycopg2" in validator.BANNED_MODULES
        assert "psycopg" in validator.BANNED_MODULES
        assert "aiomysql" in validator.BANNED_MODULES

    def test_banned_modules_contains_mq_clients(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that message queue modules are in the banned list."""
        assert "pika" in validator.BANNED_MODULES
        assert "aio_pika" in validator.BANNED_MODULES
        assert "kombu" in validator.BANNED_MODULES
        assert "celery" in validator.BANNED_MODULES

    def test_banned_modules_contains_grpc(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that gRPC module is in the banned list."""
        assert "grpc" in validator.BANNED_MODULES

    def test_banned_modules_contains_websocket(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that WebSocket modules are in the banned list."""
        assert "websockets" in validator.BANNED_MODULES
        assert "wsproto" in validator.BANNED_MODULES


class TestBannedImportDetection:
    """Tests detection of banned transport library imports."""

    def test_detects_import_kafka(self, validator: TransportValidatorModule) -> None:
        """Test detection of 'import kafka'."""
        code = """
import kafka
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "kafka"

    def test_detects_from_kafka_import(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test detection of 'from kafka import ...'."""
        code = """
from kafka import KafkaProducer
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "kafka"

    def test_detects_import_httpx(self, validator: TransportValidatorModule) -> None:
        """Test detection of 'import httpx'."""
        code = """
import httpx
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "httpx"

    def test_detects_from_aiohttp_import(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test detection of 'from aiohttp import ClientSession'."""
        code = """
from aiohttp import ClientSession
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "aiohttp"

    def test_detects_import_redis(self, validator: TransportValidatorModule) -> None:
        """Test detection of 'import redis'."""
        code = """
import redis
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "redis"

    def test_detects_import_asyncpg(self, validator: TransportValidatorModule) -> None:
        """Test detection of 'import asyncpg'."""
        code = """
import asyncpg
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "asyncpg"

    def test_detects_submodule_import(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test detection of 'from kafka.errors import KafkaError'."""
        code = """
from kafka.errors import KafkaError
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "kafka"

    def test_detects_dotted_import(self, validator: TransportValidatorModule) -> None:
        """Test detection of 'import redis.asyncio'."""
        code = """
import redis.asyncio
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "redis"

    def test_detects_aliased_import(self, validator: TransportValidatorModule) -> None:
        """Test detection of 'import kafka as k'."""
        code = """
import kafka as k
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "kafka"

    def test_detects_multiple_violations(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that multiple violations are detected."""
        code = """
import kafka
import redis
from httpx import Client
from asyncpg import connect
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 4


class TestTypeCheckingBlockHandling:
    """Tests that TYPE_CHECKING block imports are allowed."""

    def test_allows_imports_in_type_checking_block(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that imports inside TYPE_CHECKING blocks are allowed."""
        code = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import kafka
    from redis import Redis
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_typing_dot_type_checking_block(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that typing.TYPE_CHECKING blocks are recognized."""
        code = """
import typing

if typing.TYPE_CHECKING:
    import httpx
    from aiohttp import ClientSession
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_aliased_typing_type_checking_block(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that aliased typing.TYPE_CHECKING blocks are recognized.

        Pattern: import typing as t; if t.TYPE_CHECKING:
        """
        code = """
import typing as t

if t.TYPE_CHECKING:
    import kafka
    from redis import Redis
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_tp_aliased_type_checking_block(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that 'import typing as tp' aliased TYPE_CHECKING blocks work."""
        code = """
import typing as tp

if tp.TYPE_CHECKING:
    import kafka
    from redis import Redis
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_aliased_type_checking_constant(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that aliased TYPE_CHECKING constant is recognized.

        Pattern: from typing import TYPE_CHECKING as TC; if TC:
        """
        code = """
from typing import TYPE_CHECKING as TC

if TC:
    import kafka
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        # This SHOULD be allowed - aliased TYPE_CHECKING constant
        assert len(checker.violations) == 0

    def test_allows_nested_conditions_in_type_checking(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test nested conditions inside TYPE_CHECKING blocks."""
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
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_detects_imports_outside_type_checking(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that imports outside TYPE_CHECKING are still detected."""
        code = """
from typing import TYPE_CHECKING

import kafka  # This should be detected

if TYPE_CHECKING:
    import redis  # This should be allowed
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1
        assert checker.violations[0].module_name == "kafka"


class TestAllowedImports:
    """Tests that allowed imports pass validation."""

    def test_allows_typing_import(self, validator: TransportValidatorModule) -> None:
        """Test that typing imports are allowed."""
        code = """
import typing
from typing import Optional, List
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_pydantic_import(self, validator: TransportValidatorModule) -> None:
        """Test that pydantic imports are allowed."""
        code = """
from pydantic import BaseModel
import pydantic
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_allows_standard_library_imports(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that standard library imports are allowed."""
        code = """
import os
import sys
import json
import pathlib
from collections import defaultdict
from dataclasses import dataclass
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0


class TestCheckFileFunction:
    """Tests for the check_file() function."""

    def test_check_clean_file(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test checking a clean file with no banned imports."""
        test_file = tmp_path / "clean.py"
        test_file.write_text("""
import os
from typing import Optional
""")

        violations, errors = validator.check_file(test_file)

        assert len(violations) == 0
        assert len(errors) == 0

    def test_check_file_with_violations(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test checking a file with banned imports."""
        test_file = tmp_path / "bad.py"
        test_file.write_text("""
import kafka
from redis import Redis
""")

        violations, errors = validator.check_file(test_file)

        assert len(violations) == 2
        assert len(errors) == 0

    def test_check_empty_file(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test checking an empty file."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        violations, errors = validator.check_file(test_file)

        assert len(violations) == 0
        assert len(errors) == 0

    def test_check_file_syntax_error(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that files with syntax errors are handled gracefully."""
        test_file = tmp_path / "syntax_error.py"
        test_file.write_text("""
def incomplete(
""")

        violations, errors = validator.check_file(test_file)

        assert len(violations) == 0
        assert len(errors) == 1
        assert errors[0].error_type == "SyntaxError"

    def test_check_file_unicode_error(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that files with encoding errors are handled gracefully."""
        test_file = tmp_path / "encoding_error.py"
        test_file.write_bytes(b"\xff\xfe invalid utf-8 \x80\x81")

        violations, errors = validator.check_file(test_file)

        assert len(violations) == 0
        assert len(errors) == 1
        assert errors[0].error_type == "UnicodeDecodeError"

    def test_check_file_type_checking_guarded(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that TYPE_CHECKING guarded imports are allowed in files."""
        test_file = tmp_path / "guarded.py"
        test_file.write_text("""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import kafka
    from httpx import Client
""")

        violations, errors = validator.check_file(test_file)

        assert len(violations) == 0
        assert len(errors) == 0


class TestIterPythonFilesFunction:
    """Tests for the iter_python_files() function."""

    def test_finds_python_files(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test finding Python files in a directory."""
        (tmp_path / "file1.py").write_text("import os")
        (tmp_path / "file2.py").write_text("import sys")
        (tmp_path / "file.txt").write_text("not python")

        files = list(validator.iter_python_files(tmp_path, set()))

        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def test_skips_pycache_directories(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that __pycache__ directories are skipped."""
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("import kafka")
        (tmp_path / "main.py").write_text("import sys")

        files = list(validator.iter_python_files(tmp_path, set()))

        assert len(files) == 1
        assert files[0].name == "main.py"

    def test_skips_venv_directories(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that .venv and venv directories are skipped."""
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "site.py").write_text("import kafka")

        venv2 = tmp_path / "venv"
        venv2.mkdir()
        (venv2 / "site.py").write_text("import redis")

        (tmp_path / "main.py").write_text("import sys")

        files = list(validator.iter_python_files(tmp_path, set()))

        assert len(files) == 1
        assert files[0].name == "main.py"

    def test_skips_excluded_paths(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that user-provided exclusions are respected."""
        (tmp_path / "include.py").write_text("import os")
        (tmp_path / "exclude.py").write_text("import kafka")

        exclude_path = tmp_path / "exclude.py"
        files = list(validator.iter_python_files(tmp_path, {exclude_path}))

        assert len(files) == 1
        assert files[0].name == "include.py"

    def test_skips_common_cache_directories(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that common cache directories are skipped."""
        cache_dirs = [".git", ".pytest_cache", ".mypy_cache", ".ruff_cache"]
        for cache_dir in cache_dirs:
            cache = tmp_path / cache_dir
            cache.mkdir()
            (cache / "module.py").write_text("import kafka")

        (tmp_path / "main.py").write_text("import sys")

        files = list(validator.iter_python_files(tmp_path, set()))

        assert len(files) == 1
        assert files[0].name == "main.py"

    def test_finds_nested_python_files(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that Python files in nested directories are found."""
        subdir = tmp_path / "src" / "module"
        subdir.mkdir(parents=True)
        (subdir / "nested.py").write_text("import os")
        (tmp_path / "main.py").write_text("import sys")

        files = list(validator.iter_python_files(tmp_path, set()))

        assert len(files) == 2


class TestMainFunction:
    """Tests for the main() entry point."""

    def test_returns_zero_for_clean_files(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that main returns 0 when no violations found."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "clean.py").write_text("import os")

        with patch.object(
            sys,
            "argv",
            ["validate_no_transport_imports.py", "--src-dir", str(test_dir)],
        ):
            result = validator.main()
            assert result == 0

    def test_returns_one_for_violations(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that main returns 1 when violations found."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "bad.py").write_text("import kafka")

        with patch.object(
            sys,
            "argv",
            ["validate_no_transport_imports.py", "--src-dir", str(test_dir)],
        ):
            result = validator.main()
            assert result == 1

    def test_returns_one_for_nonexistent_directory(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that main returns 1 for nonexistent source directory."""
        with patch.object(
            sys,
            "argv",
            ["validate_no_transport_imports.py", "--src-dir", "/nonexistent/path"],
        ):
            result = validator.main()
            assert result == 1

    def test_exclude_flag_works(
        self, validator: TransportValidatorModule, tmp_path: Path
    ) -> None:
        """Test that --exclude flag excludes files from validation."""
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
            result = validator.main()
            assert result == 0

    def test_verbose_flag_shows_snippets(
        self,
        validator: TransportValidatorModule,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that --verbose flag shows import statement snippets."""
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
            validator.main()

        captured = capsys.readouterr()
        assert "kafka" in captured.out


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_nested_imports_in_functions(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that imports nested inside functions are detected."""
        code = """
def some_function():
    import kafka
    return kafka.KafkaProducer()
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1

    def test_handles_nested_imports_in_classes(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that imports nested inside classes are detected."""
        code = """
class MyClass:
    def __init__(self):
        import redis
        self.client = redis.Redis()
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1

    def test_string_containing_import_passes(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that strings containing import names don't trigger violations."""
        code = '''
message = "connect to redis server"
doc = """
This module uses redis for caching.
import redis  # This is just documentation
"""
'''
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_comments_containing_imports_pass(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that comments with import names don't trigger violations."""
        code = """
# import kafka  - we used to use this
# from redis import Redis
# TODO: consider using httpx
import typing
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0

    def test_try_except_imports_detected(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that imports in try/except blocks are detected."""
        code = """
try:
    import redis
except ImportError:
    redis = None
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 1

    def test_captures_correct_line_numbers(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that line numbers are correctly captured."""
        code = """

import kafka

import redis
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 2
        line_numbers = {v.line_number for v in checker.violations}
        assert 3 in line_numbers  # import kafka
        assert 5 in line_numbers  # import redis

    def test_relative_imports_not_flagged(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that relative imports without module are handled."""
        code = """
from . import models
from .. import utils
"""
        tree = ast.parse(code)
        checker = validator.TransportImportChecker(code)
        checker.visit(tree)

        assert len(checker.violations) == 0


class TestSkipDirectoriesConfiguration:
    """Tests for SKIP_DIRECTORIES configuration."""

    def test_skip_directories_contains_common_excludes(
        self, validator: TransportValidatorModule
    ) -> None:
        """Test that common excluded directories are configured."""
        expected = [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            ".pytest_cache",
            ".mypy_cache",
        ]
        for dir_name in expected:
            assert dir_name in validator.SKIP_DIRECTORIES

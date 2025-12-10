"""
Comprehensive tests for the transport import checker script.

Tests cover:
- TransportViolation dataclass
- TransportImportAnalyzer AST visitor
- analyze_file function
- find_python_files function
- get_changed_files function
- Banned import detection (kafka, redis, httpx, requests, asyncpg, etc.)
- Allowed imports (typing, pydantic, omnibase_core, standard library)
- Edge cases (empty files, syntax errors, nested imports, comments, strings)
- CLI arguments (--verbose, --json, --changed-files)
- Exit codes (0 for success, 1 for violations)
- Output formats (text, JSON)

Linear ticket: OMN-220
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Import the validation script components
# We need to add the scripts directory to path for testing.
# The defensive check prevents duplicate entries when the test module is
# reloaded (e.g., during pytest-xdist parallel execution or when running
# tests multiple times in the same Python process).
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
scripts_dir = str(SCRIPTS_DIR)
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# Module-level variables that will be populated when the script loads
# Using Any type to satisfy mypy since module may not exist at type-check time
_module_loaded = False
TransportViolation: Any = None
TransportImportAnalyzer: Any = None
TransportCheckResult: Any = None
analyze_file: Any = None
find_python_files: Any = None
get_changed_files: Any = None
main: Any = None
BANNED_TRANSPORT_MODULES: Any = None
ViolationType: Any = None
Severity: Any = None


def _load_module() -> bool:
    """Load the transport import checker module.

    Returns:
        True if module loaded successfully, False otherwise.
    """
    global _module_loaded, TransportViolation, TransportImportAnalyzer
    global TransportCheckResult, analyze_file, find_python_files, get_changed_files
    global main, BANNED_TRANSPORT_MODULES, ViolationType, Severity

    if _module_loaded:
        return True

    script_path = SCRIPTS_DIR / "check_transport_imports.py"
    if not script_path.exists():
        return False

    spec = importlib.util.spec_from_file_location(
        "check_transport_imports", script_path
    )
    if spec is None:
        return False
    if spec.loader is None:
        return False

    _module = importlib.util.module_from_spec(spec)
    # Add to sys.modules before exec to avoid dataclass issues
    sys.modules["check_transport_imports"] = _module
    spec.loader.exec_module(_module)

    # Extract the classes and functions from the loaded module
    TransportViolation = _module.TransportViolation
    TransportImportAnalyzer = _module.TransportImportAnalyzer
    TransportCheckResult = _module.TransportCheckResult
    analyze_file = _module.analyze_file
    find_python_files = _module.find_python_files
    get_changed_files = _module.get_changed_files
    main = _module.main
    BANNED_TRANSPORT_MODULES = _module.BANNED_TRANSPORT_MODULES
    ViolationType = _module.ViolationType
    Severity = _module.Severity

    _module_loaded = True
    return True


def skip_if_module_not_loaded() -> None:
    """Skip test if the module is not available."""
    if not _load_module():
        pytest.skip("Script not found: scripts/check_transport_imports.py")


# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]


class TestTransportViolation:
    """Tests for TransportViolation dataclass creation and formatting."""

    def test_violation_creation(self) -> None:
        """Test that TransportViolation can be created with all fields."""
        skip_if_module_not_loaded()

        violation = TransportViolation(
            file_path=Path("/test/file.py"),
            line_number=10,
            column=0,
            violation_type=ViolationType.BANNED_TRANSPORT_IMPORT,
            severity=Severity.ERROR,
            message="Import of 'kafka' is forbidden",
            suggestion="Use ProtocolEventBus instead",
            code_snippet="import kafka",
        )
        assert violation.file_path == Path("/test/file.py")
        assert violation.line_number == 10
        assert violation.column == 0
        assert violation.message == "Import of 'kafka' is forbidden"
        assert violation.code_snippet == "import kafka"

    def test_violation_format(self) -> None:
        """Test violation format method."""
        skip_if_module_not_loaded()

        violation = TransportViolation(
            file_path=Path("/test/file.py"),
            line_number=10,
            column=0,
            violation_type=ViolationType.BANNED_TRANSPORT_IMPORT,
            severity=Severity.ERROR,
            message="Import of 'kafka' is forbidden",
            suggestion="Use ProtocolEventBus instead",
            code_snippet="import kafka",
        )
        formatted = violation.format(verbose=True)
        assert "ERROR" in formatted
        assert "kafka" in formatted
        assert "10" in formatted


class TestBannedModulesConfiguration:
    """Tests that banned modules configuration is complete."""

    def test_banned_modules_contains_kafka(self) -> None:
        """Test that kafka is in the banned modules list."""
        skip_if_module_not_loaded()
        assert "kafka" in BANNED_TRANSPORT_MODULES

    def test_banned_modules_contains_redis(self) -> None:
        """Test that redis is in the banned modules list."""
        skip_if_module_not_loaded()
        assert "redis" in BANNED_TRANSPORT_MODULES

    def test_banned_modules_contains_httpx(self) -> None:
        """Test that httpx is in the banned modules list."""
        skip_if_module_not_loaded()
        assert "httpx" in BANNED_TRANSPORT_MODULES

    def test_banned_modules_contains_asyncpg(self) -> None:
        """Test that asyncpg is in the banned modules list."""
        skip_if_module_not_loaded()
        assert "asyncpg" in BANNED_TRANSPORT_MODULES


class TestBannedKafkaImports:
    """Tests detection of banned Kafka library imports."""

    def test_detects_import_kafka(self) -> None:
        """Test detection of 'import kafka'."""
        skip_if_module_not_loaded()

        code = """
import kafka
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "kafka" in analyzer.violations[0].message

    def test_detects_from_kafka_import(self) -> None:
        """Test detection of 'from kafka import ...'."""
        skip_if_module_not_loaded()

        code = """
from kafka import KafkaProducer
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "kafka" in analyzer.violations[0].message.lower()

    def test_detects_import_aiokafka(self) -> None:
        """Test detection of 'import aiokafka'."""
        skip_if_module_not_loaded()

        code = """
import aiokafka
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "aiokafka" in analyzer.violations[0].message

    def test_detects_from_aiokafka_import(self) -> None:
        """Test detection of 'from aiokafka import ...'."""
        skip_if_module_not_loaded()

        code = """
from aiokafka import AIOKafkaProducer
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1

    def test_detects_multiline_from_kafka_import(self) -> None:
        """Test detection of multi-line 'from kafka import (...)' statements."""
        skip_if_module_not_loaded()

        code = """
from kafka import (
    KafkaProducer,
    KafkaConsumer,
    KafkaAdminClient,
)
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        # Multi-line imports should still be detected
        assert len(analyzer.violations) == 1
        assert "kafka" in analyzer.violations[0].message.lower()


class TestBannedRedisImports:
    """Tests detection of banned Redis/Valkey library imports."""

    def test_detects_import_redis(self) -> None:
        """Test detection of 'import redis'."""
        skip_if_module_not_loaded()

        code = """
import redis
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "redis" in analyzer.violations[0].message

    def test_detects_from_redis_import(self) -> None:
        """Test detection of 'from redis import Redis'."""
        skip_if_module_not_loaded()

        code = """
from redis import Redis
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1

    def test_detects_import_valkey(self) -> None:
        """Test detection of 'import valkey'."""
        skip_if_module_not_loaded()

        code = """
import valkey
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "valkey" in analyzer.violations[0].message

    def test_detects_multiline_import_redis(self) -> None:
        """Test detection of multi-line import statements with multiple modules."""
        skip_if_module_not_loaded()

        # Note: Regular `import` statements don't support parentheses syntax.
        # But they do support comma-separated multiple imports on one line.
        code = """
import redis, json, typing
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        # Should detect redis but not json or typing
        assert len(analyzer.violations) == 1
        assert "redis" in analyzer.violations[0].message


class TestBannedHttpImports:
    """Tests detection of banned HTTP client library imports."""

    def test_detects_import_httpx(self) -> None:
        """Test detection of 'import httpx'."""
        skip_if_module_not_loaded()

        code = """
import httpx
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "httpx" in analyzer.violations[0].message

    def test_detects_from_httpx_import(self) -> None:
        """Test detection of 'from httpx import Client'."""
        skip_if_module_not_loaded()

        code = """
from httpx import Client
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1

    def test_detects_import_requests(self) -> None:
        """Test detection of 'import requests'."""
        skip_if_module_not_loaded()

        code = """
import requests
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "requests" in analyzer.violations[0].message

    def test_detects_from_aiohttp_import(self) -> None:
        """Test detection of 'from aiohttp import ClientSession'."""
        skip_if_module_not_loaded()

        code = """
from aiohttp import ClientSession
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1


class TestBannedDatabaseImports:
    """Tests detection of banned database client imports."""

    def test_detects_from_asyncpg_import(self) -> None:
        """Test detection of 'from asyncpg import connect'."""
        skip_if_module_not_loaded()

        code = """
from asyncpg import connect
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1

    def test_detects_import_asyncpg(self) -> None:
        """Test detection of 'import asyncpg'."""
        skip_if_module_not_loaded()

        code = """
import asyncpg
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "asyncpg" in analyzer.violations[0].message

    def test_detects_import_psycopg(self) -> None:
        """Test detection of 'import psycopg'."""
        skip_if_module_not_loaded()

        code = """
import psycopg
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "psycopg" in analyzer.violations[0].message

    def test_detects_import_psycopg2(self) -> None:
        """Test detection of 'import psycopg2'."""
        skip_if_module_not_loaded()

        code = """
import psycopg2
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "psycopg2" in analyzer.violations[0].message


class TestBannedInfrastructureImports:
    """Tests detection of banned infrastructure library imports."""

    def test_detects_import_hvac(self) -> None:
        """Test detection of 'import hvac' (Vault client)."""
        skip_if_module_not_loaded()

        code = """
import hvac
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "hvac" in analyzer.violations[0].message

    def test_detects_import_consul(self) -> None:
        """Test detection of 'import consul'."""
        skip_if_module_not_loaded()

        code = """
import consul
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "consul" in analyzer.violations[0].message


class TestAllowedImports:
    """Tests that allowed imports pass validation."""

    def test_allows_typing_import(self) -> None:
        """Test that 'import typing' is allowed."""
        skip_if_module_not_loaded()

        code = """
import typing
from typing import Optional, List
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 0

    def test_allows_pydantic_import(self) -> None:
        """Test that 'from pydantic import BaseModel' is allowed."""
        skip_if_module_not_loaded()

        code = """
from pydantic import BaseModel
import pydantic
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 0

    def test_allows_omnibase_core_import(self) -> None:
        """Test that 'from omnibase_core.models import X' is allowed."""
        skip_if_module_not_loaded()

        code = """
from omnibase_core.models import ModelOnexError
from omnibase_core.nodes import NodeCompute
import omnibase_core
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 0

    def test_allows_json_import(self) -> None:
        """Test that 'import json' is allowed."""
        skip_if_module_not_loaded()

        code = """
import json
from json import loads, dumps
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 0

    def test_allows_standard_library_imports(self) -> None:
        """Test that standard library imports are allowed."""
        skip_if_module_not_loaded()

        code = """
import os
import sys
import pathlib
from pathlib import Path
import datetime
from collections import defaultdict
import dataclasses
from dataclasses import dataclass
import enum
from enum import Enum
import uuid
import hashlib
import re
import abc
from abc import ABC, abstractmethod
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 0


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
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        # Imports inside TYPE_CHECKING should be allowed
        assert len(analyzer.violations) == 0

    def test_allows_typing_type_checking_block(self) -> None:
        """Test that typing.TYPE_CHECKING blocks are recognized."""
        skip_if_module_not_loaded()

        code = """
import typing

if typing.TYPE_CHECKING:
    import httpx
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        # Imports inside TYPE_CHECKING should be allowed
        assert len(analyzer.violations) == 0

    def test_allows_aliased_typing_type_checking_block(self) -> None:
        """Test that aliased typing.TYPE_CHECKING blocks are recognized.

        Some codebases use `import typing as t` for brevity, and we should
        still recognize `if t.TYPE_CHECKING:` blocks as type-checking guards.
        """
        skip_if_module_not_loaded()

        code = """
import typing as t

if t.TYPE_CHECKING:
    import kafka
    from redis import Redis
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        # Imports inside aliased TYPE_CHECKING should be allowed
        assert len(analyzer.violations) == 0

    def test_allows_tp_aliased_type_checking_block(self) -> None:
        """Test that 'import typing as tp' aliased TYPE_CHECKING blocks work.

        The `tp` alias is a common alternative to `t` for the typing module.
        This test ensures our detection handles various alias names correctly.
        """
        skip_if_module_not_loaded()

        code = """
import typing as tp

if tp.TYPE_CHECKING:
    import kafka
    from redis import Redis
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        # Imports inside tp-aliased TYPE_CHECKING should be allowed
        assert len(analyzer.violations) == 0

    def test_aliased_type_checking_constant_not_handled(self) -> None:
        """Document known limitation: aliased TYPE_CHECKING constant not detected.

        The pattern `from typing import TYPE_CHECKING as TC; if TC:` is NOT
        recognized as a type-checking block. This is a known limitation that
        is acceptable because:
        1. This pattern is extremely rare in practice
        2. Supporting it would require tracking import aliases across the AST
        3. The complexity cost outweighs the benefit

        This test documents the limitation rather than testing for correct handling.
        """
        skip_if_module_not_loaded()

        code = """
from typing import TYPE_CHECKING as TC

if TC:
    import kafka
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        # KNOWN LIMITATION: This WILL report a violation because we don't track
        # aliased TYPE_CHECKING constants. The import is inside a TC block but
        # we don't recognize TC as TYPE_CHECKING.
        assert len(analyzer.violations) == 1

    def test_allows_nested_type_checking_blocks(self) -> None:
        """Test that nested conditions inside TYPE_CHECKING blocks are handled.

        Some codebases may have additional conditions inside TYPE_CHECKING
        blocks, like version checks or platform checks.
        """
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
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        # Imports inside nested TYPE_CHECKING should be allowed
        assert len(analyzer.violations) == 0


class TestEdgeCases:
    """Tests edge cases and error handling scenarios."""

    def test_handles_empty_file(self, tmp_path: Path) -> None:
        """Test that empty files pass validation."""
        skip_if_module_not_loaded()

        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        result = analyze_file(empty_file)

        assert result.is_clean is True
        assert len(result.violations) == 0

    def test_handles_syntax_error_gracefully(self, tmp_path: Path) -> None:
        """Test that files with syntax errors are handled gracefully."""
        skip_if_module_not_loaded()

        syntax_error_file = tmp_path / "syntax_error.py"
        syntax_error_file.write_text(
            """
def incomplete_function(
"""
        )

        result = analyze_file(syntax_error_file)

        # Syntax error files should have skip_reason set
        assert result.skip_reason is not None
        assert "Syntax error" in result.skip_reason

    def test_detects_nested_imports_in_functions(self) -> None:
        """Test that imports nested inside functions are detected."""
        skip_if_module_not_loaded()

        code = """
def some_function():
    import kafka
    return kafka.KafkaProducer()
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "kafka" in analyzer.violations[0].message

    def test_detects_nested_imports_in_classes(self) -> None:
        """Test that imports nested inside classes are detected."""
        skip_if_module_not_loaded()

        code = """
class MyClass:
    def __init__(self):
        import redis
        self.client = redis.Redis()
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1

    def test_string_containing_redis_passes(self) -> None:
        """Test that strings containing 'redis' don't trigger violations."""
        skip_if_module_not_loaded()

        code = '''
message = "connect to redis server"
doc = """
This module uses redis for caching.
import redis  # This is just documentation
"""
'''
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 0

    def test_comments_containing_banned_names_pass(self) -> None:
        """Test that comments with banned import names don't trigger violations."""
        skip_if_module_not_loaded()

        code = """
# import kafka  - we used to use this
# from redis import Redis
# TODO: consider using httpx
import typing  # Not: import requests
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 0

    def test_detects_try_except_imports(self) -> None:
        """Test detection of imports in try/except blocks."""
        skip_if_module_not_loaded()

        code = """
try:
    import redis
except ImportError:
    redis = None
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        # Try/except imports should still be detected
        assert len(analyzer.violations) == 1


class TestMultipleViolations:
    """Tests detection of multiple violations in single files."""

    def test_detects_multiple_violations_same_file(self) -> None:
        """Test that multiple violations in one file are all detected."""
        skip_if_module_not_loaded()

        code = """
import kafka
import redis
import httpx
from asyncpg import connect
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 4

    def test_captures_correct_line_numbers(self) -> None:
        """Test that line numbers are correctly captured for each violation."""
        skip_if_module_not_loaded()

        code = """

import kafka

import redis
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 2
        line_numbers = {v.line_number for v in analyzer.violations}
        assert 3 in line_numbers  # import kafka
        assert 5 in line_numbers  # import redis


class TestAnalyzeFileFunction:
    """Tests for the analyze_file() function."""

    def test_analyze_clean_file(self, tmp_path: Path) -> None:
        """Test analysis of a clean file with no banned imports."""
        skip_if_module_not_loaded()

        test_file = tmp_path / "clean.py"
        test_file.write_text(
            """
import typing
from pydantic import BaseModel
import json
"""
        )

        result = analyze_file(test_file)

        assert result.is_clean is True
        assert len(result.violations) == 0
        assert result.file_path == test_file

    def test_analyze_file_with_violations(self, tmp_path: Path) -> None:
        """Test analysis of a file with banned imports."""
        skip_if_module_not_loaded()

        test_file = tmp_path / "bad.py"
        test_file.write_text(
            """
import kafka
"""
        )

        result = analyze_file(test_file)

        assert result.is_clean is False
        assert len(result.violations) == 1


class TestFindPythonFilesFunction:
    """Tests for the find_python_files() function."""

    def test_finds_python_files(self, tmp_path: Path) -> None:
        """Test finding Python files in a directory."""
        skip_if_module_not_loaded()

        (tmp_path / "file1.py").write_text("import os")
        (tmp_path / "file2.py").write_text("import sys")
        (tmp_path / "file.txt").write_text("not python")

        files = find_python_files(tmp_path)

        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def test_skips_pycache_directories(self, tmp_path: Path) -> None:
        """Test that __pycache__ directories are skipped."""
        skip_if_module_not_loaded()

        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("import os")
        (tmp_path / "main.py").write_text("import sys")

        files = find_python_files(tmp_path)

        assert len(files) == 1
        assert files[0].name == "main.py"


class TestExitCodes:
    """Tests script exit code behavior."""

    def test_returns_zero_when_no_violations(self, tmp_path: Path) -> None:
        """Test that exit code is 0 when no violations are found."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)
        (test_dir / "clean.py").write_text("import os")

        with patch.object(
            sys, "argv", ["check_transport_imports.py", "--src-dir", str(test_dir)]
        ):
            result = main()
            assert result == 0

    def test_returns_one_when_violations_found(self, tmp_path: Path) -> None:
        """Test that exit code is 1 when violations are found."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)
        (test_dir / "bad.py").write_text("import kafka")

        with patch.object(
            sys, "argv", ["check_transport_imports.py", "--src-dir", str(test_dir)]
        ):
            result = main()
            assert result == 1

    def test_returns_error_code_for_missing_path(self) -> None:
        """Test that error code 2 is returned for missing path."""
        skip_if_module_not_loaded()

        with patch.object(
            sys,
            "argv",
            ["check_transport_imports.py", "--src-dir", "/nonexistent/path"],
        ):
            result = main()
            assert result == 2


class TestOutputFormats:
    """Tests --verbose and --json output formats."""

    def test_verbose_flag_produces_detailed_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that --verbose flag produces detailed output."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)
        (test_dir / "bad.py").write_text("import kafka")

        with patch.object(
            sys,
            "argv",
            ["check_transport_imports.py", "--verbose", "--src-dir", str(test_dir)],
        ):
            main()

        captured = capsys.readouterr()
        # Verbose mode should show the violation
        assert "kafka" in captured.out.lower() or "kafka" in captured.err.lower()

    def test_json_flag_produces_valid_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that --json flag produces valid JSON output."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)
        (test_dir / "bad.py").write_text("import kafka")

        with patch.object(
            sys,
            "argv",
            ["check_transport_imports.py", "--json", "--src-dir", str(test_dir)],
        ):
            main()

        captured = capsys.readouterr()
        # Should produce valid JSON
        try:
            result = json.loads(captured.out)
            assert isinstance(result, dict)
            # JSON output should contain summary
            assert "summary" in result
        except json.JSONDecodeError:
            pytest.fail("Output was not valid JSON")

    def test_json_output_with_no_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test JSON output when there are no violations."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)
        (test_dir / "clean.py").write_text("import os")

        with patch.object(
            sys,
            "argv",
            ["check_transport_imports.py", "--json", "--src-dir", str(test_dir)],
        ):
            main()

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert isinstance(result, dict)
        # Summary should show clean files with no violations
        assert result.get("summary", {}).get("total_violations", 0) == 0


class TestAliasedImports:
    """Tests detection of aliased imports."""

    def test_detects_aliased_kafka_import(self) -> None:
        """Test detection of 'import kafka as k'."""
        skip_if_module_not_loaded()

        code = """
import kafka as k
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "kafka" in analyzer.violations[0].message

    def test_detects_aliased_from_import(self) -> None:
        """Test detection of 'from redis import Redis as R'."""
        skip_if_module_not_loaded()

        code = """
from redis import Redis as R
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1


class TestChangedFilesFlag:
    """Tests for --changed-files CLI flag behavior."""

    def test_changed_files_flag_with_no_changes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --changed-files with no changed files falls back to all files."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)
        (test_dir / "clean.py").write_text("import os")

        with patch.object(
            sys,
            "argv",
            [
                "check_transport_imports.py",
                "--changed-files",
                "--src-dir",
                str(test_dir),
            ],
        ):
            # Mock get_changed_files to return empty list (simulates no git changes)
            with patch("check_transport_imports.get_changed_files", return_value=[]):
                result = main()
                assert result == 0

    def test_changed_files_flag_filters_files(self, tmp_path: Path) -> None:
        """Test --changed-files only checks changed files."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)
        clean_file = test_dir / "clean.py"
        bad_file = test_dir / "bad.py"
        clean_file.write_text("import os")
        bad_file.write_text("import kafka")

        with patch.object(
            sys,
            "argv",
            [
                "check_transport_imports.py",
                "--changed-files",
                "--src-dir",
                str(test_dir),
            ],
        ):
            # Mock get_changed_files to only return clean file (resolved path)
            with patch(
                "check_transport_imports.get_changed_files",
                return_value=[clean_file.resolve()],
            ):
                result = main()
                # Should pass because bad.py is not in changed files
                assert result == 0

    def test_changed_files_flag_detects_violations_in_changed_files(
        self, tmp_path: Path
    ) -> None:
        """Test --changed-files detects violations in changed files."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)
        clean_file = test_dir / "clean.py"
        bad_file = test_dir / "bad.py"
        clean_file.write_text("import os")
        bad_file.write_text("import kafka")

        with patch.object(
            sys,
            "argv",
            [
                "check_transport_imports.py",
                "--changed-files",
                "--src-dir",
                str(test_dir),
            ],
        ):
            # Mock get_changed_files to return the bad file (resolved path)
            with patch(
                "check_transport_imports.get_changed_files",
                return_value=[bad_file.resolve()],
            ):
                result = main()
                # Should fail because bad.py has violations
                assert result == 1

    def test_changed_files_verbose_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --changed-files with --verbose shows mode information."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)
        clean_file = test_dir / "clean.py"
        clean_file.write_text("import os")

        with patch.object(
            sys,
            "argv",
            [
                "check_transport_imports.py",
                "--changed-files",
                "--verbose",
                "--src-dir",
                str(test_dir),
            ],
        ):
            # Mock get_changed_files to return the clean file
            with patch(
                "check_transport_imports.get_changed_files",
                return_value=[clean_file.resolve()],
            ):
                result = main()
                assert result == 0

        captured = capsys.readouterr()
        # Verbose mode should indicate changed-files mode
        assert (
            "--changed-files mode" in captured.out
            or "changed file" in captured.out.lower()
        )

    def test_changed_files_verbose_fallback_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --changed-files with --verbose shows fallback message when no changes."""
        skip_if_module_not_loaded()

        test_dir = tmp_path / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)
        (test_dir / "clean.py").write_text("import os")

        with patch.object(
            sys,
            "argv",
            [
                "check_transport_imports.py",
                "--changed-files",
                "--verbose",
                "--src-dir",
                str(test_dir),
            ],
        ):
            # Mock get_changed_files to return empty list
            with patch("check_transport_imports.get_changed_files", return_value=[]):
                result = main()
                assert result == 0

        captured = capsys.readouterr()
        # Verbose mode should indicate fallback to all files
        assert (
            "checking all files" in captured.out.lower()
            or "no changed" in captured.out.lower()
        )


class TestGetChangedFilesFunction:
    """Tests for the get_changed_files() function."""

    def test_get_changed_files_returns_empty_on_git_error(self, tmp_path: Path) -> None:
        """Test get_changed_files returns empty list when git is not available."""
        skip_if_module_not_loaded()

        # Import the function from the loaded module
        import check_transport_imports

        # Create a directory that's not a git repo
        test_dir = tmp_path / "not_a_git_repo" / "src" / "omnibase_core"
        test_dir.mkdir(parents=True)

        # Should return empty list when git fails
        result = check_transport_imports.get_changed_files(test_dir)
        assert result == []
        assert isinstance(result, list)


class TestSubmoduleImports:
    """Tests detection of submodule imports."""

    def test_detects_kafka_submodule_import(self) -> None:
        """Test detection of 'from kafka.errors import KafkaError'."""
        skip_if_module_not_loaded()

        code = """
from kafka.errors import KafkaError
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1
        assert "kafka" in analyzer.violations[0].message.lower()

    def test_detects_redis_submodule_import(self) -> None:
        """Test detection of 'import redis.asyncio'."""
        skip_if_module_not_loaded()

        code = """
import redis.asyncio
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        analyzer = TransportImportAnalyzer(
            file_path=Path("/test.py"),
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        assert len(analyzer.violations) == 1

"""
Unit tests for node purity guarantees.

AST-based purity checks to verify that declarative nodes (COMPUTE, REDUCER)
remain pure and do not contain I/O operations, network calls, or other side effects.

These tests ensure the ONEX architecture is protected from contributors adding
"convenience shortcuts" that would violate purity guarantees.

Ticket: OMN-156
"""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# Import the purity checker module
# We need to add scripts to path for the import
scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))

from collections.abc import Callable

from check_node_purity import (
    FORBIDDEN_CACHING_DECORATORS,
    FORBIDDEN_NETWORKING_MODULES,
    FORBIDDEN_PATHLIB_METHODS,
    FORBIDDEN_SUBPROCESS_MODULES,
    FORBIDDEN_THREADING_MODULES,
    VALID_NODE_BASE_CLASSES,
    PurityAnalyzer,
    PurityCheckResult,
    Severity,
    ViolationType,
    analyze_file,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def temp_node_file(tmp_path: Path) -> Callable[[str, str], Path]:
    """Factory fixture to create temporary node files for testing."""

    def _create_file(source_code: str, filename: str = "test_node.py") -> Path:
        file_path = tmp_path / filename
        file_path.write_text(textwrap.dedent(source_code).strip())
        return file_path

    return _create_file


@pytest.fixture
def analyze_source() -> Callable[[str], PurityAnalyzer]:
    """Factory fixture to analyze source code directly using two-pass approach."""
    from check_node_purity import NodeTypeFinder

    def _analyze(source_code: str) -> PurityAnalyzer:
        source = textwrap.dedent(source_code).strip()
        source_lines = source.splitlines()
        tree = ast.parse(source)

        # First pass: Find node classes and determine if file contains pure nodes
        finder = NodeTypeFinder()
        finder.visit(tree)

        # Second pass: Analyze for purity violations
        analyzer = PurityAnalyzer(
            file_path=Path("test.py"),
            source_lines=source_lines,
            node_type=finder.node_type,
            node_class_name=finder.node_class_name,
            is_pure_node=finder.is_pure_node,
        )
        analyzer.visit(tree)
        return analyzer

    return _analyze


# ==============================================================================
# TEST CLASSES
# ==============================================================================


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestPurityCheckerConfiguration:
    """Test purity checker configuration constants."""

    def test_forbidden_networking_modules_are_comprehensive(self):
        """Verify common networking libraries are forbidden."""
        expected_modules = {
            "requests",
            "httpx",
            "aiohttp",
            "urllib",
            "socket",
            "http",
            "boto3",
            "redis",
            "kafka",
        }
        for module in expected_modules:
            assert module in FORBIDDEN_NETWORKING_MODULES, f"Missing: {module}"

    def test_forbidden_subprocess_modules_are_comprehensive(self):
        """Verify subprocess modules are forbidden."""
        expected_modules = {"subprocess", "pexpect", "sh", "plumbum"}
        for module in expected_modules:
            assert module in FORBIDDEN_SUBPROCESS_MODULES, f"Missing: {module}"

    def test_forbidden_threading_modules_are_comprehensive(self):
        """Verify threading modules are forbidden."""
        expected_modules = {"threading", "multiprocessing", "concurrent.futures"}
        for module in expected_modules:
            assert module in FORBIDDEN_THREADING_MODULES, f"Missing: {module}"

    def test_forbidden_caching_decorators_are_comprehensive(self):
        """Verify caching decorators are forbidden."""
        expected_decorators = {"lru_cache", "cache", "cached_property"}
        for decorator in expected_decorators:
            assert decorator in FORBIDDEN_CACHING_DECORATORS, f"Missing: {decorator}"

    def test_forbidden_pathlib_methods_are_comprehensive(self):
        """Verify pathlib write methods are forbidden."""
        expected_methods = {"write_text", "write_bytes", "unlink", "mkdir", "touch"}
        for method in expected_methods:
            assert method in FORBIDDEN_PATHLIB_METHODS, f"Missing: {method}"

    def test_valid_base_classes_include_node_core_base(self):
        """Verify NodeCoreBase is a valid base class."""
        assert "NodeCoreBase" in VALID_NODE_BASE_CLASSES

    def test_valid_base_classes_include_generic(self):
        """Verify Generic is a valid base class."""
        assert "Generic" in VALID_NODE_BASE_CLASSES

    def test_valid_base_classes_include_mixins(self):
        """Verify Mixins are valid base classes."""
        assert "MixinFSMExecution" in VALID_NODE_BASE_CLASSES
        assert "MixinWorkflowExecution" in VALID_NODE_BASE_CLASSES


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestNetworkingImportDetection:
    """Test detection of forbidden networking imports."""

    def test_detects_requests_import(self, analyze_source):
        """Test that 'import requests' is detected."""
        source = """
        import requests
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.NETWORKING_IMPORT
            for v in analyzer.violations
        )

    def test_detects_httpx_import(self, analyze_source):
        """Test that 'import httpx' is detected."""
        source = """
        import httpx
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.NETWORKING_IMPORT and "httpx" in v.message
            for v in analyzer.violations
        )

    def test_detects_aiohttp_import(self, analyze_source):
        """Test that 'import aiohttp' is detected."""
        source = """
        import aiohttp
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.NETWORKING_IMPORT
            and "aiohttp" in v.message
            for v in analyzer.violations
        )

    def test_detects_socket_import(self, analyze_source):
        """Test that 'import socket' is detected."""
        source = """
        import socket
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.NETWORKING_IMPORT
            and "socket" in v.message
            for v in analyzer.violations
        )

    def test_detects_urllib_from_import(self, analyze_source):
        """Test that 'from urllib import ...' is detected."""
        source = """
        from urllib.request import urlopen
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.NETWORKING_IMPORT
            for v in analyzer.violations
        )

    def test_detects_boto3_import(self, analyze_source):
        """Test that 'import boto3' is detected (AWS SDK)."""
        source = """
        import boto3
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.NETWORKING_IMPORT and "boto3" in v.message
            for v in analyzer.violations
        )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestFilesystemOperationDetection:
    """Test detection of forbidden filesystem operations."""

    def test_detects_open_write_mode(self, analyze_source):
        """Test that open() with write mode is detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def write_file(self):
                with open("test.txt", "w") as f:
                    f.write("data")
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.OPEN_CALL for v in analyzer.violations
        )

    def test_detects_open_append_mode(self, analyze_source):
        """Test that open() with append mode is detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def append_file(self):
                with open("test.txt", "a") as f:
                    f.write("data")
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.OPEN_CALL for v in analyzer.violations
        )

    def test_detects_pathlib_write_text(self, analyze_source):
        """Test that Path.write_text() is detected."""
        source = """
        from pathlib import Path
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def write_file(self):
                Path("test.txt").write_text("data")
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.PATHLIB_WRITE
            and "write_text" in v.message
            for v in analyzer.violations
        )

    def test_detects_pathlib_write_bytes(self, analyze_source):
        """Test that Path.write_bytes() is detected."""
        source = """
        from pathlib import Path
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def write_file(self):
                Path("test.bin").write_bytes(b"data")
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.PATHLIB_WRITE
            and "write_bytes" in v.message
            for v in analyzer.violations
        )

    def test_detects_pathlib_unlink(self, analyze_source):
        """Test that Path.unlink() is detected."""
        source = """
        from pathlib import Path
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def delete_file(self):
                Path("test.txt").unlink()
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.PATHLIB_WRITE and "unlink" in v.message
            for v in analyzer.violations
        )

    def test_detects_pathlib_mkdir(self, analyze_source):
        """Test that Path.mkdir() is detected."""
        source = """
        from pathlib import Path
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def create_dir(self):
                Path("test_dir").mkdir()
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.PATHLIB_WRITE and "mkdir" in v.message
            for v in analyzer.violations
        )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestSubprocessDetection:
    """Test detection of forbidden subprocess operations."""

    def test_detects_subprocess_import(self, analyze_source):
        """Test that 'import subprocess' is detected."""
        source = """
        import subprocess
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.SUBPROCESS_IMPORT
            and "subprocess" in v.message
            for v in analyzer.violations
        )

    def test_detects_pexpect_import(self, analyze_source):
        """Test that 'import pexpect' is detected."""
        source = """
        import pexpect
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.SUBPROCESS_IMPORT
            and "pexpect" in v.message
            for v in analyzer.violations
        )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestThreadingDetection:
    """Test detection of forbidden threading operations."""

    def test_detects_threading_import(self, analyze_source):
        """Test that 'import threading' is detected."""
        source = """
        import threading
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.THREADING_IMPORT
            and "threading" in v.message
            for v in analyzer.violations
        )

    def test_detects_multiprocessing_import(self, analyze_source):
        """Test that 'import multiprocessing' is detected."""
        source = """
        import multiprocessing
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.THREADING_IMPORT
            and "multiprocessing" in v.message
            for v in analyzer.violations
        )

    def test_allows_concurrent_futures_in_node_compute_base(self, analyze_source):
        """Test that concurrent.futures is allowed in NodeCompute base class."""
        source = """
        from concurrent.futures import ThreadPoolExecutor
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        # Should NOT have threading violation for NodeCompute base class
        threading_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.THREADING_IMPORT
        ]
        assert len(threading_violations) == 0


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestLoggingDetection:
    """Test detection of forbidden logging imports."""

    def test_detects_logging_import(self, analyze_source):
        """Test that 'import logging' is detected."""
        source = """
        import logging
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.LOGGING_IMPORT
            for v in analyzer.violations
        )

    def test_violation_suggests_structured_logging(self, analyze_source):
        """Test that logging violation suggests structured logging."""
        source = """
        import logging
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        logging_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LOGGING_IMPORT
        ]
        assert len(logging_violations) == 1
        assert "structured logging" in logging_violations[0].suggestion.lower()


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestClassMutableDataDetection:
    """Test detection of class-level mutable data."""

    def test_detects_class_level_list(self, analyze_source):
        """Test that class-level list is detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            items = []  # Mutable!
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.CLASS_MUTABLE_DATA
            and "items" in v.message
            for v in analyzer.violations
        )

    def test_detects_class_level_dict(self, analyze_source):
        """Test that class-level dict is detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            cache = {}  # Mutable!
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.CLASS_MUTABLE_DATA
            and "cache" in v.message
            for v in analyzer.violations
        )

    def test_detects_class_level_set(self, analyze_source):
        """Test that class-level set is detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            seen = set()  # Mutable!
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.CLASS_MUTABLE_DATA
            for v in analyzer.violations
        )

    def test_detects_class_level_list_call(self, analyze_source):
        """Test that class-level list() call is detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            items = list()  # Mutable!
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.CLASS_MUTABLE_DATA
            for v in analyzer.violations
        )

    def test_allows_dunder_attributes(self, analyze_source):
        """Test that dunder attributes are allowed."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            __slots__ = []
        """
        analyzer = analyze_source(source)

        # Should NOT have mutable data violation for __slots__
        mutable_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.CLASS_MUTABLE_DATA
        ]
        assert len(mutable_violations) == 0


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestCachingDecoratorDetection:
    """Test detection of forbidden caching decorators."""

    def test_detects_lru_cache_decorator(self, analyze_source):
        """Test that @lru_cache is detected."""
        source = """
        from functools import lru_cache
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            @lru_cache
            def compute(self, x):
                return x * 2
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.CACHING_DECORATOR
            and "lru_cache" in v.message
            for v in analyzer.violations
        )

    def test_detects_cache_decorator(self, analyze_source):
        """Test that @cache is detected."""
        source = """
        from functools import cache
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            @cache
            def compute(self, x):
                return x * 2
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.CACHING_DECORATOR
            for v in analyzer.violations
        )

    def test_detects_cached_property_decorator(self, analyze_source):
        """Test that @cached_property is detected."""
        source = """
        from functools import cached_property
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            @cached_property
            def computed_value(self):
                return 42
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.CACHING_DECORATOR
            for v in analyzer.violations
        )

    def test_violation_suggests_model_compute_cache(self, analyze_source):
        """Test that caching violation suggests ModelComputeCache."""
        source = """
        from functools import lru_cache
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            @lru_cache
            def compute(self, x):
                return x * 2
        """
        analyzer = analyze_source(source)

        caching_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.CACHING_DECORATOR
        ]
        assert len(caching_violations) >= 1
        assert any("ModelComputeCache" in v.suggestion for v in caching_violations)


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestInheritanceValidation:
    """Test validation of node inheritance."""

    def test_allows_node_core_base_inheritance(self, analyze_source):
        """Test that inheriting from NodeCoreBase is allowed."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        inheritance_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.INVALID_INHERITANCE
        ]
        assert len(inheritance_violations) == 0

    def test_allows_generic_inheritance(self, analyze_source):
        """Test that inheriting from Generic is allowed."""
        source = """
        from typing import Generic, TypeVar
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        T = TypeVar('T')

        class NodeMyReducer(NodeCoreBase, Generic[T]):
            pass
        """
        analyzer = analyze_source(source)

        inheritance_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.INVALID_INHERITANCE
        ]
        assert len(inheritance_violations) == 0

    def test_allows_mixin_inheritance(self, analyze_source):
        """Test that inheriting from Mixins is allowed."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution

        class NodeMyReducer(NodeCoreBase, MixinFSMExecution):
            pass
        """
        analyzer = analyze_source(source)

        inheritance_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.INVALID_INHERITANCE
        ]
        assert len(inheritance_violations) == 0

    def test_detects_invalid_base_class(self, analyze_source):
        """Test that invalid base classes are detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class SomeOtherClass:
            pass

        class NodeMyCompute(NodeCoreBase, SomeOtherClass):
            pass
        """
        analyzer = analyze_source(source)

        inheritance_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.INVALID_INHERITANCE
        ]
        assert len(inheritance_violations) == 1
        assert "SomeOtherClass" in inheritance_violations[0].message


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestNodeTypeDetection:
    """Test detection of node types."""

    def test_detects_compute_node(self, analyze_source):
        """Test that compute nodes are detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.node_type == "compute"
        assert analyzer.is_pure_node is True

    def test_detects_reducer_node(self, analyze_source):
        """Test that reducer nodes are detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyReducer(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.node_type == "reducer"
        assert analyzer.is_pure_node is True

    def test_detects_effect_node_not_pure(self, analyze_source):
        """Test that effect nodes are NOT marked as pure."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyEffect(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.node_type == "effect"
        assert analyzer.is_pure_node is False

    def test_detects_orchestrator_node_not_pure(self, analyze_source):
        """Test that orchestrator nodes are NOT marked as pure."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyOrchestrator(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.node_type == "orchestrator"
        assert analyzer.is_pure_node is False


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestEffectNodesAreNotChecked:
    """Test that effect nodes allow I/O operations."""

    def test_effect_node_allows_networking(self, analyze_source):
        """Test that effect nodes can import networking libraries."""
        source = """
        import requests
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeApiEffect(NodeCoreBase):
            def fetch(self):
                return requests.get("http://example.com")
        """
        analyzer = analyze_source(source)

        # Effect node - not a pure node, so no violations should be tracked
        assert analyzer.node_type == "effect"
        assert analyzer.is_pure_node is False
        # Violations list should be empty because we only check pure nodes
        assert len(analyzer.violations) == 0

    def test_effect_node_allows_filesystem(self, analyze_source):
        """Test that effect nodes can use filesystem operations."""
        source = """
        from pathlib import Path
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeFileEffect(NodeCoreBase):
            def write(self):
                Path("test.txt").write_text("data")
        """
        analyzer = analyze_source(source)

        assert analyzer.node_type == "effect"
        assert len(analyzer.violations) == 0


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestFileAnalysis:
    """Test full file analysis."""

    def test_analyze_pure_node_file(self, temp_node_file):
        """Test analyzing a pure node file."""
        source = """
        from typing import Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodePureCompute(NodeCoreBase):
            def __init__(self, container):
                super().__init__(container)
                self.items = []  # Instance-level is fine

            def compute(self, data: Any) -> Any:
                return data
        """
        file_path = temp_node_file(source, "node_pure_compute.py")
        result = analyze_file(file_path)

        assert result.node_class_name == "NodePureCompute"
        assert result.node_type == "compute"
        assert result.is_pure is True
        assert len(result.violations) == 0

    def test_analyze_impure_node_file(self, temp_node_file):
        """Test analyzing an impure node file."""
        source = """
        import requests
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeImpureCompute(NodeCoreBase):
            cache = {}  # Class-level mutable

            def compute(self, url: str) -> str:
                return requests.get(url).text
        """
        file_path = temp_node_file(source, "node_impure_compute.py")
        result = analyze_file(file_path)

        assert result.node_class_name == "NodeImpureCompute"
        assert result.is_pure is False
        assert len(result.violations) >= 2  # At least networking + mutable data


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestViolationSeverity:
    """Test that violations have correct severity levels."""

    def test_networking_import_is_error(self, analyze_source):
        """Test that networking imports are ERROR severity."""
        source = """
        import requests
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        networking_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.NETWORKING_IMPORT
        ]
        assert all(v.severity == Severity.ERROR for v in networking_violations)

    def test_caching_decorator_is_error(self, analyze_source):
        """Test that caching decorators are ERROR severity."""
        source = """
        from functools import lru_cache
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            @lru_cache
            def compute(self, x):
                return x
        """
        analyzer = analyze_source(source)

        caching_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.CACHING_DECORATOR
        ]
        assert all(v.severity == Severity.ERROR for v in caching_violations)


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestActualNodeFiles:
    """Test actual node files in the codebase for purity."""

    @pytest.fixture
    def src_dir(self) -> Path:
        """Get source directory."""
        return Path(__file__).parent.parent.parent.parent / "src" / "omnibase_core"

    def test_node_compute_is_analyzed(self, src_dir):
        """Test that NodeCompute can be analyzed."""
        node_compute_path = src_dir / "nodes" / "node_compute.py"
        if not node_compute_path.exists():
            pytest.skip("NodeCompute file not found")

        result = analyze_file(node_compute_path)

        # The base class may have violations or not - just verify it's analyzed
        assert result.node_class_name == "NodeCompute"
        assert result.node_type == "compute"

    def test_node_reducer_is_analyzed(self, src_dir):
        """Test that NodeReducer can be analyzed."""
        node_reducer_path = src_dir / "nodes" / "node_reducer.py"
        if not node_reducer_path.exists():
            pytest.skip("NodeReducer file not found")

        result = analyze_file(node_reducer_path)

        assert result.node_class_name == "NodeReducer"
        assert result.node_type == "reducer"

    def test_node_effect_skipped(self, src_dir):
        """Test that NodeEffect is skipped (not a pure node).

        Effect nodes are explicitly skipped from purity checks since they are
        designed to handle I/O operations. The analyzer should:
        1. Correctly identify the node type as "effect"
        2. Set skip_reason (indicating purity checks were skipped)
        3. Mark is_pure as True (since no violations are checked)
        4. Have an empty violations list
        """
        node_effect_path = src_dir / "nodes" / "node_effect.py"
        if not node_effect_path.exists():
            pytest.skip("NodeEffect file not found")

        result = analyze_file(node_effect_path)

        # Verify node type detection
        assert result.node_type == "effect", (
            f"Expected node_type='effect', got '{result.node_type}'"
        )

        # Effect nodes MUST have skip_reason set - this is the key indicator
        # that purity checks were intentionally skipped for this node type
        assert result.skip_reason is not None, (
            "Effect nodes must have skip_reason set to indicate purity checks "
            "were skipped. Got skip_reason=None which would indicate the node "
            "was analyzed for purity violations (incorrect for EFFECT nodes)."
        )
        assert "Not a pure node" in result.skip_reason, (
            f"Expected skip_reason to contain 'Not a pure node', "
            f"got: '{result.skip_reason}'"
        )

        # When skipped, is_pure should be True (no violations found/checked)
        assert result.is_pure is True, (
            f"Expected is_pure=True for skipped effect node, got {result.is_pure}"
        )

        # Violations list should be empty since no checks were performed
        assert len(result.violations) == 0, (
            f"Expected no violations for skipped effect node, "
            f"got {len(result.violations)} violations"
        )

    def test_node_orchestrator_skipped(self, src_dir):
        """Test that NodeOrchestrator is skipped (not a pure node).

        Orchestrator nodes are explicitly skipped from purity checks since they
        coordinate workflows and may need to interact with external systems.
        The analyzer should:
        1. Correctly identify the node type as "orchestrator"
        2. Set skip_reason (indicating purity checks were skipped)
        3. Mark is_pure as True (since no violations are checked)
        4. Have an empty violations list
        """
        node_orch_path = src_dir / "nodes" / "node_orchestrator.py"
        if not node_orch_path.exists():
            pytest.skip("NodeOrchestrator file not found")

        result = analyze_file(node_orch_path)

        # Verify node type detection
        assert result.node_type == "orchestrator", (
            f"Expected node_type='orchestrator', got '{result.node_type}'"
        )

        # Orchestrator nodes MUST have skip_reason set - this is the key indicator
        # that purity checks were intentionally skipped for this node type
        assert result.skip_reason is not None, (
            "Orchestrator nodes must have skip_reason set to indicate purity "
            "checks were skipped. Got skip_reason=None which would indicate the "
            "node was analyzed for purity violations (incorrect for ORCHESTRATOR nodes)."
        )
        assert "Not a pure node" in result.skip_reason, (
            f"Expected skip_reason to contain 'Not a pure node', "
            f"got: '{result.skip_reason}'"
        )

        # When skipped, is_pure should be True (no violations found/checked)
        assert result.is_pure is True, (
            f"Expected is_pure=True for skipped orchestrator node, got {result.is_pure}"
        )

        # Violations list should be empty since no checks were performed
        assert len(result.violations) == 0, (
            f"Expected no violations for skipped orchestrator node, "
            f"got {len(result.violations)} violations"
        )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestViolationFormatting:
    """Test violation message formatting."""

    def test_violation_includes_line_number(self, analyze_source):
        """Test that violations include line numbers."""
        source = """
        import requests
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert len(analyzer.violations) > 0
        for violation in analyzer.violations:
            assert violation.line_number > 0

    def test_violation_includes_suggestion(self, analyze_source):
        """Test that violations include suggestions."""
        source = """
        import requests
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert len(analyzer.violations) > 0
        for violation in analyzer.violations:
            assert len(violation.suggestion) > 0
            assert (
                "Effect" in violation.suggestion or "container" in violation.suggestion
            )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestAllowedPatterns:
    """Test that allowed patterns don't trigger violations."""

    def test_allows_typing_imports(self, analyze_source):
        """Test that typing imports are allowed."""
        source = """
        from typing import Any, Dict, List, Optional, TypeVar
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        # No forbidden import violations
        forbidden_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.FORBIDDEN_IMPORT
            and v.severity == Severity.ERROR
        ]
        assert len(forbidden_violations) == 0

    def test_allows_pydantic_imports(self, analyze_source):
        """Test that pydantic imports are allowed."""
        source = """
        from pydantic import BaseModel, Field
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        forbidden_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.FORBIDDEN_IMPORT
            and v.severity == Severity.ERROR
        ]
        assert len(forbidden_violations) == 0

    def test_allows_hashlib_import(self, analyze_source):
        """Test that hashlib is allowed (deterministic hashing)."""
        source = """
        import hashlib
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def hash_data(self, data: str) -> str:
                return hashlib.sha256(data.encode()).hexdigest()
        """
        analyzer = analyze_source(source)

        forbidden_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.FORBIDDEN_IMPORT
            and v.severity == Severity.ERROR
        ]
        assert len(forbidden_violations) == 0

    def test_allows_time_perf_counter(self, analyze_source):
        """Test that time module is allowed (for metrics)."""
        source = """
        import time
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def compute(self, data):
                start = time.perf_counter()
                result = self._process(data)
                duration = time.perf_counter() - start
                return result
        """
        analyzer = analyze_source(source)

        forbidden_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.FORBIDDEN_IMPORT
            and v.severity == Severity.ERROR
        ]
        assert len(forbidden_violations) == 0

    def test_allows_omnibase_core_imports(self, analyze_source):
        """Test that omnibase_core imports are allowed."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        forbidden_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.FORBIDDEN_IMPORT
            and v.severity == Severity.ERROR
        ]
        assert len(forbidden_violations) == 0

    def test_allows_open_read_mode(self, analyze_source):
        """Test that open() with read mode is allowed."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def read_file(self, path: str) -> str:
                with open(path, "r") as f:
                    return f.read()
        """
        analyzer = analyze_source(source)

        open_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.OPEN_CALL
        ]
        assert len(open_violations) == 0

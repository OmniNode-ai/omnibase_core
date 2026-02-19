# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Shared fixtures for validation tests.

This module provides common fixtures for purity linter tests, including the
analyze_source fixture that is used by test_declarative_node_purity_linter.py.

IMPORTANT: This module should only contain pytest fixtures, not type exports.
For shared types (PurityAnalyzer, Severity, ViolationType, etc.), import from
purity_test_helpers.py instead. Importing from conftest.py as a regular module
is an anti-pattern that should be avoided.

Ticket: OMN-203
"""

from __future__ import annotations

import ast
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

# Import types from the helper module (not directly from scripts)
# This avoids sys.path mutation in conftest.py
from tests.unit.validation.purity_test_helpers import (
    NodeTypeFinder,
    PurityAnalyzer,
)


@pytest.fixture
def analyze_source() -> Callable[[str], PurityAnalyzer]:
    """Factory fixture to analyze source code directly using two-pass approach.

    This fixture provides a function that:
    1. Parses source code into an AST
    2. First pass: Find node classes and determine if file contains pure nodes
    3. Second pass: Analyze for purity violations

    Returns:
        A callable that takes source code string and returns a PurityAnalyzer
        with violation results.

    Example:
        def test_detects_networking_import(analyze_source):
            source = '''
            import requests
            from omnibase_core.infrastructure.node_core_base import NodeCoreBase

            class NodeMyCompute(NodeCoreBase):
                pass
            '''
            analyzer = analyze_source(source)
            assert any(
                v.violation_type == ViolationType.NETWORKING_IMPORT
                for v in analyzer.violations
            )
    """

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


@pytest.fixture
def temp_node_file(tmp_path: Path) -> Callable[[str, str], Path]:
    """Factory fixture to create temporary node files for testing.

    Returns:
        A callable that creates a temporary file with the given source code
        and filename.

    Example:
        def test_analyze_file(temp_node_file):
            source = '''
            from omnibase_core.infrastructure.node_core_base import NodeCoreBase

            class NodePureCompute(NodeCoreBase):
                pass
            '''
            file_path = temp_node_file(source, "node_compute.py")
            result = analyze_file(file_path)
            assert result.is_pure is True
    """

    def _create_file(source_code: str, filename: str = "test_node.py") -> Path:
        file_path = tmp_path / filename
        file_path.write_text(textwrap.dedent(source_code).strip())
        return file_path

    return _create_file


# Only export fixtures, not types
# For types (PurityAnalyzer, Severity, ViolationType), import from purity_test_helpers.py
__all__ = [
    "analyze_source",
    "temp_node_file",
]

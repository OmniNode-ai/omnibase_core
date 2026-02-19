# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test helpers for purity linter tests.

This module provides shared types and utilities for purity linter tests.
These are re-exported from the check_node_purity script for use in tests.

The sys.path modification is necessary because:
1. The check_node_purity.py script is in the scripts/ directory
2. It's not a proper Python package (no __init__.py)
3. mypy cannot resolve dynamic imports via importlib

This approach is used instead of conftest.py exports because:
- conftest.py should only provide pytest fixtures
- Importing from conftest.py as a regular module is an anti-pattern
- Helper modules are the proper place for shared test utilities

Ticket: OMN-203
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
# This is necessary for mypy to resolve types correctly from the check_node_purity module
_scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
if str(_scripts_path) not in sys.path:
    sys.path.insert(0, str(_scripts_path))

# Import and re-export types from check_node_purity
from check_node_purity import (
    NodeTypeFinder,
    PurityAnalyzer,
    Severity,
    ViolationType,
)

__all__ = [
    "NodeTypeFinder",
    "PurityAnalyzer",
    "Severity",
    "ViolationType",
]

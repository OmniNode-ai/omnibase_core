# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX Runtime Module.

Runtime infrastructure for ONEX node execution,
including contract file loading.

Components:
    - FileRegistry: Loads YAML contract files with fail-fast validation

Related:
    - OMN-229: FileRegistry for contract file loading
"""

from omnibase_core.runtime.runtime_file_registry import FileRegistry

__all__ = [
    "FileRegistry",
]

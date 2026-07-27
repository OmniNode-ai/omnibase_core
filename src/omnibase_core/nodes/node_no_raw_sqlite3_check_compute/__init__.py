# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_raw_sqlite3_check COMPUTE node package (OMN-14659).

Exposes :class:`NodeNoRawSqlite3CheckCompute` — AST-scans explicit (path,
source) pairs for raw ``sqlite3.connect()`` calls outside adapter
definitions, and returns a ``ModelValidationReport``.
"""

from omnibase_core.nodes.node_no_raw_sqlite3_check_compute.handler import (
    NodeNoRawSqlite3CheckCompute,
)

__all__ = ["NodeNoRawSqlite3CheckCompute"]

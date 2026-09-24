# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""work_ledger_state COMPUTE node package (OMN-19405, typed work ledger T4).

Exposes :class:`NodeWorkLedgerStateCompute`, the pure fold of a JSON-lines
work ledger into a ``ModelWorkLedgerState``. The queries over that state live
in :mod:`.queries`.
"""

from omnibase_core.nodes.node_work_ledger_state_compute.handler import (
    NodeWorkLedgerStateCompute,
)

__all__ = ["NodeWorkLedgerStateCompute"]

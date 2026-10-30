# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The gate protocol is a faithful view of the handler module's public surface (OMN-17427).

``ProtocolDoneWriteReceiptGate`` types the module surface of
``node_done_write_receipt_gate_compute`` that a contract-driven caller binds.
Every non-``decide`` member must be exported by the handler module and callable,
so a rename in the handler fails here and not at a caller's resolution time.
"""

from __future__ import annotations

import pytest

from omnibase_core.nodes.node_done_write_receipt_gate_compute import (
    handler_done_write_receipt_gate as handler_module,
)
from omnibase_core.nodes.node_done_write_receipt_gate_compute.protocol_done_write_receipt_gate import (
    ProtocolDoneWriteReceiptGate,
)
from omnibase_core.nodes.node_done_write_receipt_gate_compute.protocol_done_write_receipt_queries import (
    ProtocolDoneWriteReceiptQueries,
)

pytestmark = pytest.mark.unit


def _module_members() -> tuple[str, ...]:
    return tuple(
        name
        for protocol in ProtocolDoneWriteReceiptGate.__mro__
        for name in protocol.__dict__
        if not name.startswith("_") and name != "decide"
    )


def test_gate_protocol_extends_the_queries_protocol() -> None:
    assert issubclass(ProtocolDoneWriteReceiptGate, ProtocolDoneWriteReceiptQueries)


@pytest.mark.parametrize("name", _module_members())
def test_handler_module_exports_every_protocol_member(name: str) -> None:
    assert name in handler_module.__all__
    assert callable(getattr(handler_module, name))

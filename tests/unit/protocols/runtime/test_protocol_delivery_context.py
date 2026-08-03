# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RED-first tests for the structural ``ProtocolDeliveryContext`` (OMN-15665).

Structural drift guard, mirroring the existing
``tests/unit/protocols/runtime/test_protocol_transport.py`` convention: the
concrete ``ModelDeliveryContext`` must satisfy the protocol WITHOUT the protocol
importing the model — a ``protocols -> models`` edge is frozen at its ceiling
(OMN-14340 growth ratchet, ``scripts/ci/check_import_ratchet.py``) and a new edge
hard-fails CI.
"""

from __future__ import annotations

import uuid

from omnibase_core.models.runtime.model_delivery_context import ModelDeliveryContext
from omnibase_core.protocols.runtime.protocol_delivery_context import (
    ProtocolDeliveryContext,
)


def test_model_delivery_context_satisfies_protocol_structurally() -> None:
    ctx = ModelDeliveryContext(
        envelope_id=uuid.uuid4(), topic="onex.cmd.x.v1", partition=0, offset=1
    )
    assert isinstance(ctx, ProtocolDeliveryContext)


def test_protocol_module_does_not_import_models() -> None:
    """Ratchet guard: the protocol module itself imports no ``omnibase_core.models``
    symbol — it is purely structural (properties typed with primitives / stdlib
    ``UUID`` only)."""
    import ast
    import inspect

    from omnibase_core.protocols.runtime import protocol_delivery_context

    source = inspect.getsource(protocol_delivery_context)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("omnibase_core.models"), (
                f"protocol_delivery_context.py must not import from "
                f"{node.module} (protocols -> models edge is frozen)"
            )

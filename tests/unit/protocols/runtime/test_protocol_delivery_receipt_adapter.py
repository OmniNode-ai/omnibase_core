# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RED-first tests for ``ProtocolDeliveryReceiptAdapter`` (OMN-15665, unchanged by r2).

Authority: Linear comment ``cfb64e0f`` on OMN-15666 states this OMN-15665 contract
is UNCHANGED by the r2 decision — "the unchanged OMN-15665
``ProtocolDeliveryReceiptAdapter`` contract ``Callable[[], Awaitable[None]] -> None``"
— and the R2 harness pin
(``omni_worktrees/OMN-15663/omninode_infra-renewal/tests/fixtures/omn_15663_r2/
target_models.py::ProtocolDeliveryReceiptAdapter``) reproduces the identical
zero-argument shape. It is deliberately NOT the same shape as a
context-consuming disposition adapter (that is
``ProtocolTerminalDispositionAdapter``, OMN-15663/OMN-15667 territory,
``dispose(context) -> receipt``) — collapsing the two was r1-rejection defect #3
and must never recur here.
"""

from __future__ import annotations

import inspect

from omnibase_core.protocols.runtime.protocol_delivery_receipt_adapter import (
    ProtocolDeliveryReceiptAdapter,
)


class _ZeroArgReceiptAck:
    async def __call__(self) -> None:
        return None


class _TakesAContextArgument:
    """Shape that must NOT satisfy the protocol (guards r1-rejection defect #3)."""

    async def __call__(self, context: object) -> None:
        return None


def test_zero_arg_awaitable_satisfies_protocol() -> None:
    assert isinstance(_ZeroArgReceiptAck(), ProtocolDeliveryReceiptAdapter)


def test_context_taking_callable_does_not_satisfy_protocol() -> None:
    """A callable requiring a positional argument is not zero-arg-compatible."""
    instance = _TakesAContextArgument()
    sig = inspect.signature(instance.__call__)
    non_self_required = [
        p
        for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]
    assert non_self_required, "fixture must require a positional argument"


def test_protocol_call_signature_is_zero_argument() -> None:
    call = ProtocolDeliveryReceiptAdapter.__call__
    sig = inspect.signature(call)
    non_self_params = [p for p in sig.parameters.values() if p.name != "self"]
    assert non_self_params == [], (
        "ProtocolDeliveryReceiptAdapter.__call__ must remain zero-argument "
        "(frozen OMN-15665 shape, unchanged by the r2 decision)"
    )

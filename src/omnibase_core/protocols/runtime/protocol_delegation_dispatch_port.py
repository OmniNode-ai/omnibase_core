# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The one delegation dispatch port every implementation satisfies (OMN-19838)."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

RequestT_contra = TypeVar("RequestT_contra", contravariant=True)
ResultT_co = TypeVar("ResultT_co", covariant=True)


@runtime_checkable
class ProtocolDelegationDispatchPort(Protocol[RequestT_contra, ResultT_co]):
    """Dispatch one delegation request and return its terminal result.

    Bind it to the delegation dispatch models where a port is declared or
    checked::

        ProtocolDelegationDispatchPort[
            ModelDelegationDispatchRequest, ModelDelegationDispatchResult
        ]

    both from ``omnibase_core.models.delegation.wire``. Every implementation,
    in any repo, has exactly that one method shape. A new dispatch option is a
    new defaulted field on the request model, never a new parameter here.

    The protocol is generic because this module must not import
    ``omnibase_core.models``: the protocols -> models import edges are frozen at
    their ceiling by the OMN-14340 growth ratchet
    (``scripts/ci/check_import_ratchet.py``), the same constraint
    ``ProtocolDeliveryContext`` meets structurally.

    It is async because the consumer handler awaits every implementation inside
    ``asyncio.wait_for``. ``isinstance`` against this protocol checks only that
    a ``dispatch`` attribute exists; signature conformance is a static check
    (``mypy --strict``), never a runtime one.
    """

    async def dispatch(self, request: RequestT_contra) -> ResultT_co:
        """Dispatch ``request`` and return the terminal result."""
        ...


__all__ = ["ProtocolDelegationDispatchPort"]

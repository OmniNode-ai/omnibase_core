# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The bus the validator runtime publishes through, as the container holds it (OMN-21529)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelValidatorRuntimeBus", "PublishFn"]

# The publish call every bus backend exposes: ``publish(topic, key, value)``.
PublishFn = Callable[[str, bytes | None, bytes], Awaitable[None]]


class ModelValidatorRuntimeBus(BaseModel):
    """The lifecycle and publish calls of the bus an overlay binds.

    The container registers one under this type; the report writer resolves it with
    ``get_service`` and never builds a bus. The calls belong to whichever bus the
    overlay names, so the in-memory bus and a broker bus are interchangeable here.
    """

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, arbitrary_types_allowed=True
    )

    start: Callable[[], Awaitable[None]]
    publish: PublishFn
    close: Callable[[], Awaitable[None]]

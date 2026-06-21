# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Protocol for local runtime publishable payload models."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolLocalRuntimePayloadModel(Protocol):
    """Payload model shape used for local runtime bus publication."""

    correlation_id: object

    def model_dump_json(self) -> str:
        """Serialize the payload as JSON."""
        raise NotImplementedError


__all__: list[str] = ["ProtocolLocalRuntimePayloadModel"]

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ProtocolHarnessInferenceAdapter: inference seam for the local runtime harness (OMN-13420)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.runtime.harness.model_inference_request import (
        ModelInferenceRequest,
    )
    from omnibase_core.models.runtime.harness.model_inference_result import (
        ModelInferenceResult,
    )


@runtime_checkable
class ProtocolHarnessInferenceAdapter(Protocol):
    """Minimal inference shape used by the harness EFFECT handler.

    Implementations sit behind this seam so the harness never names a concrete
    backend: a recorded-fixture adapter (offline) or a curl-subprocess adapter
    (separate-binary LAN access) both satisfy it.
    """

    @property
    def adapter_id(self) -> str:
        """Return a stable adapter identifier for evidence/provenance."""
        raise NotImplementedError  # stub-ok: protocol declaration only

    def infer(self, request: ModelInferenceRequest) -> ModelInferenceResult:
        """Run inference and return a completion."""
        raise NotImplementedError  # stub-ok: protocol declaration only


__all__ = ["ProtocolHarnessInferenceAdapter"]

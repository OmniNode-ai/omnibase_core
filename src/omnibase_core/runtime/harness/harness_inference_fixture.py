# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Recorded-fixture inference adapter for the local runtime harness (OMN-13420).

Fully offline; returns a recorded completion. The default adapter for proof runs
so the DoD ("no LAN required") holds with zero config.
"""

from __future__ import annotations

from omnibase_core.models.runtime.harness.model_inference_request import (
    ModelInferenceRequest,
)
from omnibase_core.models.runtime.harness.model_inference_result import (
    ModelInferenceResult,
)


class RecordedFixtureInferenceAdapter:
    """Offline inference adapter — returns a recorded completion. No LAN, no I/O.

    When ``completion`` is omitted it echoes a deterministic completion derived
    from the prompt so runs are reproducible.
    """

    def __init__(
        self, completion: str | None = None, model: str = "recorded-fixture"
    ) -> None:
        self._completion = completion
        self._model = model

    @property
    def adapter_id(self) -> str:
        """Return the adapter provenance identifier."""
        return "fixture"

    def infer(self, request: ModelInferenceRequest) -> ModelInferenceResult:
        """Return the recorded (or prompt-echoed) completion."""
        completion = (
            self._completion
            if self._completion is not None
            else f"[recorded] {request.prompt}"
        )
        return ModelInferenceResult(
            completion=completion,
            model=self._model,
            adapter=self.adapter_id,
        )


__all__ = ["RecordedFixtureInferenceAdapter"]

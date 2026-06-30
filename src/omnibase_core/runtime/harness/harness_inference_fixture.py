# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Recorded-fixture inference adapter for the local runtime harness (OMN-13420).

Fully offline; replays a completion that was **recorded from a real model call**
(golden-chain replay). It never derives the completion from the prompt: a
prompt-echo would let a harness run report ``terminal_status: success`` while
generating nothing — a false-green stub (OMN-13496). A recorded completion is
therefore mandatory; constructing the adapter without one fails fast.
"""

from __future__ import annotations

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.harness.model_inference_request import (
    ModelInferenceRequest,
)
from omnibase_core.models.runtime.harness.model_inference_result import (
    ModelInferenceResult,
)


class RecordedFixtureInferenceAdapter:
    """Offline inference adapter — replays a recorded completion. No LAN, no I/O.

    ``completion`` MUST be a non-empty string recorded from a real model call.
    There is no prompt-echo / prompt-derived default: that path produced a
    false-green where a run generated nothing yet reported success (OMN-13496).
    """

    def __init__(self, completion: str, model: str = "recorded-fixture") -> None:
        if not completion.strip():
            raise ModelOnexError(
                message=(
                    "RecordedFixtureInferenceAdapter requires a non-empty completion "
                    "recorded from a real model call; prompt-echo / empty completions "
                    "are a false-green stub (OMN-13496)."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        self._completion = completion
        self._model = model

    @property
    def adapter_id(self) -> str:
        """Return the adapter provenance identifier."""
        return "fixture"

    def infer(self, request: ModelInferenceRequest) -> ModelInferenceResult:
        """Return the recorded completion (replayed, never derived from the prompt)."""
        return ModelInferenceResult(
            completion=self._completion,
            model=self._model,
            adapter=self.adapter_id,
        )


__all__ = ["RecordedFixtureInferenceAdapter"]

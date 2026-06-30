# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Curl-subprocess inference adapter for the local runtime harness (OMN-13420).

Shells out to the ``curl`` binary. A separate binary carries its own macOS Local
Network grant, so it sidesteps the per-binary Python LAN-grant problem, and it
keeps ``httpx`` off the harness path. Imperative ``curl`` is acceptable here
because it stays behind the inference-adapter protocol seam.
"""

from __future__ import annotations

import json
import subprocess

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.harness.model_inference_request import (
    ModelInferenceRequest,
)
from omnibase_core.models.runtime.harness.model_inference_result import (
    ModelInferenceResult,
)


class CurlSubprocessInferenceAdapter:
    """Inference adapter that shells out to ``curl`` (separate-binary LAN access).

    Posts an OpenAI-compatible chat-completion request to ``endpoint`` and parses
    ``choices[0].message.content`` from the response.
    """

    def __init__(
        self,
        endpoint: str,
        model: str,
        *,
        timeout_seconds: float = 30.0,
        curl_binary: str = "curl",
    ) -> None:
        self._endpoint = endpoint
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._curl_binary = curl_binary

    @property
    def adapter_id(self) -> str:
        """Return the adapter provenance identifier."""
        return "curl"

    def infer(self, request: ModelInferenceRequest) -> ModelInferenceResult:
        """Run inference via a curl subprocess and parse the completion."""
        body = json.dumps(
            {
                "model": self._model,
                "max_tokens": request.max_tokens,
                "messages": [{"role": "user", "content": request.prompt}],
            }
        )
        completed = (
            subprocess.run(  # boundary-ok: dev-harness inference behind adapter seam
                [
                    self._curl_binary,
                    "-sS",
                    "-X",
                    "POST",
                    self._endpoint,
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    body,
                ],
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        )
        if completed.returncode != 0:
            raise ModelOnexError(
                message=(
                    f"curl inference failed (exit {completed.returncode}): "
                    f"{completed.stderr.strip()}"
                ),
                error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
            )
        try:
            parsed = json.loads(completed.stdout)
            completion = parsed["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ModelOnexError(
                message=f"curl inference returned unparseable response: {exc}",
                error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
            ) from exc
        return ModelInferenceResult(
            completion=str(completion),
            model=self._model,
            adapter=self.adapter_id,
        )


__all__ = ["CurlSubprocessInferenceAdapter"]

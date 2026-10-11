# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Inference Bridge Adapter — bridges orchestrator to node_llm_inference_effect.

OWNER module (OMN-13208 / A1 re-home). Shared across review/grader nodes
(node_hostile_reviewer, node_pr_review_bot, node_adr_*_llm_effect,
node_pr_semantic_grader_llm_effect) so no node reaches into a sibling node's
internal handler package.

Resolves model configuration, constructs OpenAI-compatible requests, dispatches
via HTTP or CLI subprocess, and returns raw response text. Defines the
``ModelInferenceAdapter`` ABC consumed by reviewer/grader handlers.

The durable target (OMN-13210 / B1) replaces in-handler HTTP/CLI dispatch with
an INTENT_TO_EFFECT hop to the canonical inference effect node via contract
``model_routing`` + ``secret_store_resolver``; this A1 re-home preserves the
existing dispatch behavior while relocating ownership.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from typing import Final, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from omnimarket.inference.protocol_config import (
    ModelInferenceProtocolSelection,
    apply_inference_protocol,
)

logger = logging.getLogger(__name__)

_RESERVED_EXTRA_HEADER_NAMES: Final[frozenset[str]] = frozenset(
    {"authorization", "content-type"}
)
_RESERVED_PROTOCOL_REQUEST_KEYS: Final[frozenset[str]] = frozenset(
    {"model", "messages", "max_tokens", "temperature", "response_format"}
)


class ModelInferenceAdapter(ABC):
    """Protocol for dispatching inference to node_llm_inference_effect."""

    @abstractmethod
    async def infer(
        self,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
        temperature: float | None = None,
        response_format: ModelInferenceJsonObjectResponseFormat | None = None,
        protocol_selection: ModelInferenceProtocolSelection | None = None,
    ) -> str:
        """Send prompt to a model and return raw response text."""
        ...


class ModelInferenceJsonObjectResponseFormat(BaseModel):
    """The single structured-output response format supported by this bridge.

    This is deliberately a typed caller-owned request value rather than a
    provider protocol profile option.  A profile may shape a provider request,
    but it may not select or override an application's output contract.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["json_object"] = "json_object"


class ModelInferenceBridgeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_configs: dict[str, dict[str, object]] = Field(
        default_factory=dict,
        description="Per-logical-route config: base_url, model_id, transport, context_window, timeout_seconds",
    )


class AdapterInferenceBridge(ModelInferenceAdapter):
    """Concrete inference adapter using OpenAI-compatible HTTP or CLI subprocess."""

    def __init__(self, config: ModelInferenceBridgeConfig) -> None:
        self._config = config

    async def infer(
        self,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
        temperature: float | None = None,
        response_format: ModelInferenceJsonObjectResponseFormat | None = None,
        protocol_selection: ModelInferenceProtocolSelection | None = None,
    ) -> str:
        model_cfg = self._config.model_configs.get(model_key)
        if model_cfg is None:
            msg = f"Unknown model_key: {model_key!r}"
            raise ValueError(msg)

        transport = str(model_cfg.get("transport", "http"))
        if transport == "cli":
            if protocol_selection is not None:
                msg = (
                    f"Model route {model_key!r} uses cli transport, which does not "
                    "support provider protocol selection"
                )
                raise ValueError(msg)
            if response_format is not None:
                msg = (
                    f"Model route {model_key!r} uses cli transport, which does not "
                    "support a structured response_format"
                )
                raise ValueError(msg)
            return await self._call_cli_model(
                model_key, model_cfg, system_prompt, user_prompt, timeout_seconds
            )
        return await self._call_http_model(
            model_key,
            model_cfg,
            system_prompt,
            user_prompt,
            timeout_seconds,
            temperature,
            response_format,
            protocol_selection,
        )

    async def _call_http_model(
        self,
        model_key: str,
        cfg: dict[str, object],
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
        temperature: float | None,
        response_format: ModelInferenceJsonObjectResponseFormat | None,
        protocol_selection: ModelInferenceProtocolSelection | None,
    ) -> str:
        base_url = str(cfg.get("base_url", ""))
        if not base_url:
            base_url_env = str(cfg.get("base_url_env", ""))
            base_url = os.environ.get(base_url_env, "")
        if not base_url:
            msg = f"Model route {model_key!r} is missing base_url"
            raise ValueError(msg)

        model_id = str(cfg.get("model_id", ""))
        if not model_id:
            msg = f"Model route {model_key!r} is missing model_id"
            raise ValueError(msg)

        api_key = str(cfg.get("api_key", "")) or None

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        raw_temperature = (
            temperature if temperature is not None else cfg.get("temperature", 0.2)
        )
        if not isinstance(raw_temperature, (int, float, str)):
            raw_temperature = 0.2

        extra_headers = cfg.get("extra_headers")
        if isinstance(extra_headers, dict):
            for k, v in extra_headers.items():
                header_name = str(k)
                if header_name.lower() in _RESERVED_EXTRA_HEADER_NAMES:
                    logger.warning("Ignoring reserved extra header: %s", header_name)
                    continue
                headers[header_name] = str(v)

        (
            shaped_system_prompt,
            shaped_user_prompt,
            protocol_request_options,
        ) = apply_inference_protocol(
            system_prompt=system_prompt,
            prompt=user_prompt,
            model=model_id,
            selection=protocol_selection,
        )
        reserved_protocol_keys = _RESERVED_PROTOCOL_REQUEST_KEYS.intersection(
            protocol_request_options
        )
        if reserved_protocol_keys:
            keys = ", ".join(sorted(reserved_protocol_keys))
            raise ValueError(f"protocol request options cannot override: {keys}")

        payload: dict[str, object] = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": shaped_system_prompt},
                {"role": "user", "content": shaped_user_prompt},
            ],
            "max_tokens": 2048,
            "temperature": float(raw_temperature),
        }
        payload.update(protocol_request_options)
        if response_format is not None:
            payload["response_format"] = response_format.model_dump(mode="json")

        # OMN-15152 repro #1: a caller-supplied base_url may already carry a
        # /v1 suffix (e.g. "http://host:port/v1"). Appending "/v1/chat/..."
        # unconditionally produced ".../v1/v1/chat/completions" -> a 404 that
        # the orchestrator then silently swallowed into a clean 0-findings
        # result. Normalize so the suffix is never doubled.
        normalized_base = base_url.rstrip("/")
        if normalized_base.endswith("/v1"):
            url = f"{normalized_base}/chat/completions"
        else:
            url = f"{normalized_base}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(
                url,
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0]["message"]
            # OMN-15152 repro #2: some OpenAI-compatible reasoning-model
            # responses land the actual text in `message.reasoning` or
            # `message.reasoning_content` and leave `content` empty/absent. A
            # bare `message["content"]` index then raised an undiagnosable
            # KeyError('content') that the caller swallowed into a clean
            # 0-findings result. Tolerate these reasoning-shape responses;
            # only fail with a clear, specific error when none of the
            # supported fields carries usable text.
            content = (
                message.get("content")
                or message.get("reasoning")
                or message.get("reasoning_content")
            )
            if not content:
                msg = (
                    f"Model route {model_key!r} response has no content, reasoning, "
                    f"or reasoning_content text: {message!r}"
                )
                raise ValueError(msg)
            return str(content)

    async def _call_cli_model(
        self,
        model_key: str,
        cfg: dict[str, object],
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
    ) -> str:
        cli_command = str(cfg.get("cli_command", ""))
        if not cli_command:
            msg = f"Model route {model_key!r} is missing cli_command"
            raise ValueError(msg)
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        # Non-blocking subprocess dispatch: a synchronous subprocess.run() here
        # would stall the event loop for the full CLI-model latency, starving
        # every concurrent infer() / review / grader task on the same loop.
        proc = await asyncio.create_subprocess_exec(
            cli_command,
            combined_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, _stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_seconds
            )
        except TimeoutError as exc:
            # Preserve the prior subprocess.run(timeout=...) contract: reap the
            # still-running child, then surface subprocess.TimeoutExpired so
            # callers catching the original exception type keep working.
            proc.kill()
            await proc.wait()
            raise subprocess.TimeoutExpired(
                cmd=[cli_command, combined_prompt], timeout=timeout_seconds
            ) from exc
        # check=False semantics preserved: non-zero exit is tolerated; we return
        # whatever the CLI wrote to stdout regardless of returncode.
        return stdout_bytes.decode().strip()


__all__: list[str] = [
    "AdapterInferenceBridge",
    "ModelInferenceAdapter",
    "ModelInferenceBridgeConfig",
    "ModelInferenceJsonObjectResponseFormat",
]

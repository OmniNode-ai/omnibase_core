# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""vLLM inference backend for NodeLocalLlmInferenceEffect.

Implements ProtocolLocalLlmInference by calling an OpenAI-compatible
chat-completions endpoint (vLLM, TGI, or any compatible server). The endpoint
is resolved from the canonical bifrost routing contract
(:class:`~omniclaude.handlers.handler_contract_endpoint_resolver.HandlerContractEndpointResolver`); the
contract's complete URL is posted to verbatim.

Concurrency is bounded by an asyncio.Semaphore (env: OMNICLAUDE_VLLM_MAX_CONCURRENT).
A single httpx.AsyncClient is reused across calls for connection pooling.

Reference pattern: node_agent_routing_compute/handler_routing_llm.py:393-446.

Ticket: OMN-2799, OMN-5722
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any  # any-ok: external API boundary

import httpx

from omniclaude.enums.enum_contract_capability import EnumContractCapability
from omniclaude.handlers.handler_contract_endpoint_resolver import (
    HandlerContractEndpointResolver,
)
from omniclaude.models.model_contract_endpoint import (
    OPENAI_CHAT_COMPLETIONS_SUFFIX,
)
from omniclaude.nodes.node_local_llm_inference_effect.models import (
    ModelLocalLlmInferenceRequest,
)
from omniclaude.shared.models.model_skill_result import (
    ModelSkillResult,
    SkillResultStatus,
)

logger = logging.getLogger(__name__)

# Mapping from model_purpose literals to the routing-contract capability that
# serves them. A purpose the contract declares no local capability for maps to
# None and answers BACKEND_UNAVAILABLE; a key absent here is an unknown purpose.
_MAP_PURPOSE: dict[str, EnumContractCapability | None] = {
    "CODE_ANALYSIS": EnumContractCapability.CODE_GENERATION,
    "REASONING": EnumContractCapability.REASONING,
    "ROUTING": EnumContractCapability.CLASSIFICATION,
    "GENERAL": EnumContractCapability.DOCUMENTATION,
    "EMBEDDING": EnumContractCapability.EMBEDDING,
    "VISION": None,
    "FUNCTION_CALLING": None,
}

# Type alias for untyped dicts at the OpenAI API boundary.
_JsonDict = dict[str, Any]  # ONEX_EXCLUDE: dict_str_any - external/untyped API boundary


@dataclass
class ChatCompletionResult:
    """Result of a chat completion call with optional tool calls.

    Mirrors the structure needed by the agentic loop (OMN-5722).
    """

    content: str | None = None
    tool_calls: list[_JsonDict] = field(default_factory=list)
    error: str | None = None


def _parse_tool_calls_from_message(
    message: _JsonDict,
) -> list[_JsonDict]:
    """Extract and normalize tool_calls from an OpenAI chat completion message.

    Mirrors ``_parse_tool_calls`` from ``handler_llm_openai_compatible.py:861-907``.
    Handles both well-formed tool_calls arrays and malformed/partial responses.

    Args:
        message: The ``choices[0].message`` dict from the API response.

    Returns:
        List of normalized tool call dicts with ``id``, ``function.name``,
        and ``function.arguments`` (as a JSON string).
    """
    raw_calls = message.get("tool_calls")
    if not raw_calls or not isinstance(raw_calls, list):
        return []

    parsed: list[_JsonDict] = []
    for call in raw_calls:
        if not isinstance(call, dict):
            continue

        func = call.get("function", {})
        if not isinstance(func, dict):
            continue

        name = func.get("name")
        if not name:
            continue

        # Arguments may be a string (normal) or a dict (some backends).
        args_raw = func.get("arguments", "{}")
        if isinstance(args_raw, dict):
            args_str = json.dumps(args_raw)
        elif isinstance(args_raw, str):
            args_str = args_raw
        else:
            args_str = "{}"

        parsed.append(
            {
                "id": call.get("id", f"call_{len(parsed)}"),
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": args_str,
                },
            }
        )

    return parsed


def _parse_chat_completion_response(
    data: _JsonDict,
) -> ChatCompletionResult:
    """Parse a full chat completion response into a ChatCompletionResult.

    Args:
        data: The raw JSON response from the chat-completions endpoint.

    Returns:
        ChatCompletionResult with content and/or tool_calls populated.
    """
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("chat_completion response missing choices: %s", exc)
        return ChatCompletionResult(error="MALFORMED_RESPONSE")

    content = message.get("content")
    tool_calls = _parse_tool_calls_from_message(message)

    return ChatCompletionResult(content=content, tool_calls=tool_calls)


class VllmInferenceBackend:
    """vLLM/OpenAI-compatible inference backend.

    Sends POST requests to the endpoint's configured chat-completions path and parses
    ``choices[0].message.content`` from the response.

    Satisfies ``ProtocolLocalLlmInference`` (runtime-checkable).

    Attributes:
        handler_key: Backend identifier for handler routing (``"vllm"``).
    """

    handler_key: str = "vllm"

    # --- Synchronous chat_completion for agentic loop (OMN-5722) ---

    def chat_completion_sync(
        self,
        messages: list[_JsonDict],
        endpoint_url: str,
        model: str | None = None,
        tools: list[_JsonDict] | None = None,
        tool_choice: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        chat_completions_path: str = OPENAI_CHAT_COMPLETIONS_SUFFIX,
    ) -> ChatCompletionResult:
        """Synchronous chat completion with tool-calling support.

        Sends a full messages array (with optional tools) to a chat-completions
        endpoint and parses the response, including any ``tool_calls`` in the
        assistant message.

        This method is intentionally synchronous for use in the delegation daemon's
        background thread (the agentic loop runs in a threading context, not asyncio).

        Args:
            messages: OpenAI-format messages list.
            endpoint_url: Base URL of the LLM endpoint (e.g. ``http://host:8000/``).
            model: Model name override. Falls back to ``"default"`` if not provided.
            tools: Optional list of tool definitions (OpenAI function-calling format).
            tool_choice: Optional tool choice directive (``"auto"``, ``"none"``, etc.).
            max_tokens: Optional max tokens for the response.
            temperature: Optional temperature for the response.
            chat_completions_path: Path appended to ``endpoint_url``. Defaults to
                the config-declared OpenAI-compatible path; pass the endpoint's
                ``chat_completions_path`` for providers that differ.

        Returns:
            ChatCompletionResult with content and/or tool_calls.
        """
        url = f"{endpoint_url.rstrip('/')}{chat_completions_path}"
        payload: _JsonDict = {
            "model": model or "default",
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        try:
            with httpx.Client(
                timeout=self._TIMEOUT, transport=self._sync_transport
            ) as client:
                response = client.post(url, json=payload)
        except httpx.TimeoutException:
            logger.warning("chat_completion timed out for %s", url)
            return ChatCompletionResult(error="TIMEOUT")
        except httpx.NetworkError as exc:
            logger.warning("chat_completion network error: %s", exc)
            return ChatCompletionResult(error="BACKEND_UNAVAILABLE")

        if response.status_code != 200:
            logger.warning("chat_completion HTTP %d from %s", response.status_code, url)
            return ChatCompletionResult(error=f"HTTP {response.status_code}")

        data = response.json()
        return _parse_chat_completion_response(data)

    _MAX_CONCURRENT: int = int(os.getenv("OMNICLAUDE_VLLM_MAX_CONCURRENT", "4"))
    _TIMEOUT: httpx.Timeout = httpx.Timeout(
        connect=5.0, read=120.0, write=10.0, pool=5.0
    )

    def __init__(
        self,
        endpoints: HandlerContractEndpointResolver,
        *,
        sync_transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Initialize the vLLM inference backend.

        Args:
            endpoints: Resolver of local endpoints from the routing contract.
            sync_transport: Optional httpx transport for the synchronous
                ``chat_completion_sync`` client. Defaults to ``None`` (httpx's
                real network transport). Supplying a custom transport is the
                idiomatic httpx injection seam — production may pass a pooled or
                proxied transport, and tests pass an ``httpx.MockTransport`` to
                exercise the REAL request-serialization + error-handling paths
                without a live endpoint.
        """
        self._endpoints = endpoints
        self._client = httpx.AsyncClient(timeout=self._TIMEOUT)
        self._semaphore = asyncio.Semaphore(self._MAX_CONCURRENT)
        self._sync_transport = sync_transport

    async def infer(self, request: ModelLocalLlmInferenceRequest) -> ModelSkillResult:
        """Submit a prompt to the vLLM endpoint and return a ModelSkillResult.

        Resolves the endpoint from the routing contract using the request's
        model_purpose (defaults to ``"CODE_ANALYSIS"`` when not specified). The
        prompt is sent as a single user message to the contract's complete URL.

        Args:
            request: Inference request with prompt and optional parameters.

        Returns:
            ModelSkillResult with status SUCCESS and the LLM output, or
            status FAILED with an appropriate error string.
        """
        # Resolve purpose string to a contract capability.
        purpose_key = request.model_purpose or "CODE_ANALYSIS"
        if purpose_key not in _MAP_PURPOSE:
            return ModelSkillResult(
                skill_name=request.skill_name,
                status=SkillResultStatus.FAILED,
                error=f"Unknown model_purpose: {purpose_key!r}",
                correlation_id=request.correlation_id,
            )

        capability = _MAP_PURPOSE[purpose_key]
        endpoint = self._endpoints.resolve(capability) if capability else None
        if endpoint is None:
            logger.warning(
                "No endpoint configured for purpose=%s",
                purpose_key,
            )
            return ModelSkillResult(
                skill_name=request.skill_name,
                status=SkillResultStatus.FAILED,
                error=f"BACKEND_UNAVAILABLE: no endpoint for purpose={purpose_key}",
                correlation_id=request.correlation_id,
            )

        url = endpoint.url
        payload: dict[  # ONEX_EXCLUDE: dict_str_any - external/untyped API boundary
            str, Any
        ] = {  # ONEX_EXCLUDE: dict_str_any - external/untyped API boundary
            "model": request.model or endpoint.model_name,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        async with self._semaphore:
            try:
                response = await self._client.post(url, json=payload)
            except httpx.TimeoutException:
                logger.warning("vLLM inference timed out")
                return ModelSkillResult(
                    skill_name=request.skill_name,
                    status=SkillResultStatus.FAILED,
                    error="TIMEOUT",
                    correlation_id=request.correlation_id,
                )
            except httpx.NetworkError as exc:
                logger.warning("vLLM network error: %s", exc)
                return ModelSkillResult(
                    skill_name=request.skill_name,
                    status=SkillResultStatus.FAILED,
                    error="BACKEND_UNAVAILABLE",
                    correlation_id=request.correlation_id,
                )

            if response.status_code != 200:
                logger.warning("vLLM returned HTTP %d", response.status_code)
                return ModelSkillResult(
                    skill_name=request.skill_name,
                    status=SkillResultStatus.FAILED,
                    error=f"HTTP {response.status_code}",
                    correlation_id=request.correlation_id,
                )

            data = response.json()

            try:
                content: str = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                logger.warning("vLLM response missing choices: %s", exc)
                return ModelSkillResult(
                    skill_name=request.skill_name,
                    status=SkillResultStatus.FAILED,
                    error="BACKEND_UNAVAILABLE: malformed response (missing choices)",
                    correlation_id=request.correlation_id,
                )

        return ModelSkillResult(
            skill_name=request.skill_name,
            status=SkillResultStatus.SUCCESS,
            output=content,
            correlation_id=request.correlation_id,
        )

    async def aclose(self) -> None:
        """Close the underlying httpx client.

        Must be called during plugin shutdown to release connections.
        """
        await self._client.aclose()


__all__ = ["ChatCompletionResult", "VllmInferenceBackend"]

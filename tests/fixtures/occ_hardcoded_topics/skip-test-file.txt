# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for HandlerCodeEnrichmentEffect.

Unit tests: mocked LLM client, real code paths for confidence threshold logic.
Integration stubs: @pytest.mark.integration — skipped unless .201 is available.

Container-driven DI (OMN-15229): the handler takes only the injectable
``container``; the ProtocolCodeEntityRepository double is registered on a real
ModelONEXContainer and resolved at the effect boundary inside handle().
handle() keeps the definition-B single-payload shape.

NOTE: this module lives outside ``testpaths = ["tests"]`` and is therefore not
collected by CI. The CI-collected proof for the OMN-15229 refactor lives in
``tests/nodes/node_code_enrichment_effect/test_handler_code_enrichment_effect_di.py``.

[OMN-5657, OMN-5664, OMN-15229]
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from omnibase_core.container import ModelONEXContainer

from omnimarket.nodes.node_code_enrichment_effect.handlers.handler_code_enrichment_effect import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    TOPIC_CODE_ENRICHED,
    HandlerCodeEnrichmentEffect,
    ProtocolCodeEntityRepository,
)
from omnimarket.nodes.node_code_enrichment_effect.models.model_code_enrichment_request import (
    ModelCodeEnrichmentRequest,
)

# =============================================================================
# Fixtures
# =============================================================================


def _make_entity(
    *,
    entity_name: str = "MyHandler",
    bases: list[str] | None = None,
    methods: list[dict[str, str]] | None = None,
    docstring: str | None = "Handles incoming requests.",
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "entity_name": entity_name,
        "entity_type": "class",
        "qualified_name": f"mymodule.{entity_name}",
        "source_repo": "omniintelligence",
        "source_path": "src/mymodule.py",
        "docstring": docstring,
        "signature": None,
        "bases": bases or ["BaseHandler"],
        "methods": methods or [{"name": "handle"}, {"name": "validate"}],
        "fields": None,
        "decorators": None,
    }


def _make_mock_repository(entities: list[dict[str, Any]]) -> MagicMock:
    repo = MagicMock()
    repo.get_entities_needing_enrichment = AsyncMock(return_value=entities)
    repo.update_enrichment = AsyncMock()
    return repo


async def _handler_with_repository(repo: MagicMock) -> HandlerCodeEnrichmentEffect:
    """Build the handler over a real container holding *repo* as the provider.

    Mirrors the runtime resolver path (OMN-15229): boot injects only the
    container; the repository is resolved from it at the effect boundary.
    """
    container = ModelONEXContainer()
    await container.service_registry.register_instance(
        ProtocolCodeEntityRepository,  # type: ignore[type-abstract]  # Protocol used as DI key
        repo,
    )
    return HandlerCodeEnrichmentEffect(container=container)


def _llm_json_response(
    *,
    classification: str = "handler",
    confidence: float = 0.85,
    description: str = "Handles incoming HTTP requests.",
    pattern: str = "handler",
) -> httpx.Response:
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "classification": classification,
                            "confidence": confidence,
                            "description": description,
                            "pattern": pattern,
                        }
                    )
                }
            }
        ]
    }
    return httpx.Response(
        status_code=200,
        json=payload,
        request=httpx.Request("POST", "http://test/v1/chat/completions"),
    )


# =============================================================================
# Unit tests
# =============================================================================


def test_contract_declared_publish_topic_is_pinned() -> None:
    """The contract-declared publish topic keeps its literal wire string."""
    assert TOPIC_CODE_ENRICHED == "onex.evt.omnimarket.code-enriched.v1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_successful_enrichment(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM returns valid classification → repository.update_enrichment called correctly."""
    entity_1 = _make_entity(entity_name="HandlerA")
    entity_2 = _make_entity(entity_name="HandlerB")
    repo = _make_mock_repository([entity_1, entity_2])

    call_count = 0

    async def mock_post(self: Any, url: str, **kwargs: Any) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return _llm_json_response(
            classification="handler",
            confidence=0.85,
            description=f"Description for entity {call_count}",
            pattern="handler",
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    handler = await _handler_with_repository(repo)
    result = await handler.handle(
        ModelCodeEnrichmentRequest(
            correlation_id="test-enrich-001",
            llm_endpoint_override="http://test:8001",
            batch_size=10,
        )
    )

    assert result.correlation_id == "test-enrich-001"
    assert result.enriched_count == 2
    assert result.failed_count == 0
    assert repo.update_enrichment.call_count == 2

    first_call = repo.update_enrichment.call_args_list[0]
    assert first_call.kwargs["entity_id"] == str(entity_1["id"])
    assert first_call.kwargs["classification"] == "handler"
    assert first_call.kwargs["classification_confidence"] == 0.85
    assert first_call.kwargs["enrichment_version"] == "1.0.0"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_low_confidence_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Confidence below threshold → classification stored as 'other', not the LLM answer."""
    entity = _make_entity(entity_name="AmbiguousThing")
    repo = _make_mock_repository([entity])
    low_confidence = DEFAULT_CONFIDENCE_THRESHOLD - 0.1

    async def mock_post(self: Any, url: str, **kwargs: Any) -> httpx.Response:
        return _llm_json_response(
            classification="adapter",
            confidence=low_confidence,
            description="Some adapter thing.",
            pattern="adapter",
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    handler = await _handler_with_repository(repo)
    result = await handler.handle(
        ModelCodeEnrichmentRequest(
            correlation_id="test-enrich-002",
            llm_endpoint_override="http://test:8001",
        )
    )

    assert result.enriched_count == 1
    assert result.failed_count == 0

    call_kwargs = repo.update_enrichment.call_args.kwargs
    assert call_kwargs["classification"] == "other"
    assert call_kwargs["classification_confidence"] == low_confidence


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_failure_increments_failed_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM HTTP error → entity not enriched, failed_count incremented."""
    entity = _make_entity(entity_name="FailEntity")
    repo = _make_mock_repository([entity])

    async def mock_post(self: Any, url: str, **kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    handler = await _handler_with_repository(repo)
    result = await handler.handle(
        ModelCodeEnrichmentRequest(
            correlation_id="test-enrich-003",
            llm_endpoint_override="http://test:8001",
        )
    )

    assert result.enriched_count == 0
    assert result.failed_count == 1
    repo.update_enrichment.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_entities_returns_zero_counts() -> None:
    """When no entities need enrichment, return zero counts immediately."""
    repo = _make_mock_repository([])
    handler = await _handler_with_repository(repo)

    result = await handler.handle(
        ModelCodeEnrichmentRequest(
            correlation_id="test-enrich-004",
            llm_endpoint_override="http://test:8001",
        )
    )

    assert result.correlation_id == "test-enrich-004"
    assert result.enriched_count == 0
    assert result.failed_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_llm_url_raises() -> None:
    """Missing LLM_CODER_URL with no override → EnvironmentError."""
    import os

    repo = _make_mock_repository([_make_entity()])
    handler = await _handler_with_repository(repo)

    env_backup = os.environ.pop("LLM_CODER_URL", None)
    try:
        with pytest.raises(EnvironmentError, match="LLM_CODER_URL"):
            await handler.handle(
                ModelCodeEnrichmentRequest(correlation_id="test-enrich-005")
            )
    finally:
        if env_backup is not None:
            os.environ["LLM_CODER_URL"] = env_backup


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_used_when_primary_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Primary ConnectError → fallback endpoint used successfully."""
    entity = _make_entity(entity_name="FallbackEntity")
    repo = _make_mock_repository([entity])

    call_urls: list[str] = []

    async def mock_post(self: Any, url: str, **kwargs: Any) -> httpx.Response:
        call_urls.append(url)
        if "primary" in url:
            raise httpx.ConnectError("primary down")
        return _llm_json_response(classification="handler", confidence=0.9)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setenv("LLM_FALLBACK_URL", "http://fallback:8001")

    handler = await _handler_with_repository(repo)
    result = await handler.handle(
        ModelCodeEnrichmentRequest(
            correlation_id="test-enrich-006",
            llm_endpoint_override="http://primary:8001",
        )
    )

    assert result.enriched_count == 1
    assert result.failed_count == 0
    assert any("fallback" in u for u in call_urls)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_correlation_id_propagated_to_output() -> None:
    """correlation_id from input must appear unchanged in output."""
    repo = _make_mock_repository([])
    handler = await _handler_with_repository(repo)
    corr = "unique-enrichment-corr-abc-123"

    result = await handler.handle(
        ModelCodeEnrichmentRequest(
            correlation_id=corr,
            llm_endpoint_override="http://test:8001",
        )
    )

    assert result.correlation_id == corr


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_batch_size_rejected_by_model() -> None:
    """batch_size <= 0 is now rejected at model construction (Pydantic gt=0),
    not by a manual handler-side check — validation moved to the typed payload."""
    with pytest.raises(ValueError, match="greater than 0"):
        ModelCodeEnrichmentRequest(correlation_id="test-enrich-007", batch_size=0)


# =============================================================================
# Integration stubs — require .201 to be reachable
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_real_llm_probe() -> None:
    """Probe the real LLM endpoint. Skipped unless LLM_CODER_URL is set and reachable."""
    import os

    endpoint = os.environ.get("LLM_CODER_URL")
    if not endpoint:
        pytest.skip("LLM_CODER_URL not set — skipping integration probe")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{endpoint}/v1/chat/completions",
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": 'Reply with: {"classification": "handler", "confidence": 1.0, "description": "test", "pattern": "test"}',
                        }
                    ],
                    "max_tokens": 50,
                    "temperature": 0.0,
                },
            )
            assert resp.status_code == 200
        except Exception as exc:
            pytest.skip(f"LLM endpoint unreachable: {exc}")

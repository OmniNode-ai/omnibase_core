# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler for code entity embedding generation and Qdrant storage.

Re-implements the embedding logic from omniintelligence dispatch_handler_code_embedding
(deleted in PR #568) as a proper omnimarket EFFECT node handler.

Design invariants (from recovered source + OMN-5657 contract):
  - Embedding endpoint URL comes from EMBEDDING_MODEL_URL env var — fail-fast if unset.
  - Qdrant collection name comes from QDRANT_CODE_COLLECTION (default: code_patterns).
  - Point ID = entity UUID — upsert is idempotent, never duplicates.
  - Qdrant unavailability is a graceful skip (warning + zero counts), not an error.
  - Tiered fields: primary (entity_name, signature, docstring) always included;
    secondary (llm_description) appended when available.
  - correlation_id is required on both input and output.

[OMN-5657, OMN-5665]
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

import httpx

from omnimarket.nodes.node_code_embedding_effect.models.model_code_embedding_request import (
    ModelCodeEmbeddingRequest,
)
from omnimarket.nodes.node_code_embedding_effect.models.model_code_embedding_result import (
    ModelCodeEmbeddingResult,
)
from omnimarket.protocols.protocol_code_entity_repository import (
    ProtocolCodeEntityRepository,
)

if TYPE_CHECKING:
    from omnibase_core.container import ModelONEXContainer

logger = logging.getLogger(__name__)

# Topic bindings from contract.yaml event_bus
TOPIC_CODE_ENTITIES_EXTRACTED: str = "onex.evt.omnimarket.code-entities-extracted.v1"  # onex-topic-allow: pending contract auto-wiring
TOPIC_CODE_EMBEDDED: str = "onex.evt.omnimarket.code-embedded.v1"  # onex-topic-allow: pending contract auto-wiring

DEFAULT_QDRANT_COLLECTION = "code_patterns"
DEFAULT_EMBEDDING_BATCH_SIZE = 50
DEFAULT_VECTOR_SIZE = 4096

PRIMARY_FIELDS = ("entity_name", "docstring", "signature")
SECONDARY_FIELDS = ("llm_description",)


class HandlerCodeEmbeddingEffect:
    """EFFECT handler — embeds code entities and stores vectors in Qdrant.

    Container-driven pattern (OMN-15228, copying the OMN-13603 precedent in
    ``node_ticket_query``): the constructor takes only the injectable
    ``container``, so ``ServiceHandlerResolver`` can build this handler at boot
    from known-param injection alone (``event_bus``, ``container``,
    ``ownership_query``). Before this change ``repository`` was a required,
    default-less ctor param, which quarantined the handler at boot and tripped
    the OMN-13551 guard (``tests/test_handler_routing_boot_resolvable.py``).

    ``ProtocolCodeEntityRepository`` (canonical declaration in
    ``omnimarket.protocols.protocol_code_entity_repository`` since OMN-15230;
    this module used to declare its own same-named copy) is resolved from the
    container at the effect boundary inside ``handle()`` — at the point of first
    use, so the
    documented "Qdrant unavailability is a graceful skip" invariant above is
    preserved exactly (a batch that skips on Qdrant never needed a repository).
    Resolution fails loud when no provider is registered: an embedding EFFECT
    with no entity repository cannot do its job, so the caller must see the
    wiring gap rather than a zero-count result. No silent fallback, no
    null-object repository.

    ``qdrant_client`` stays a defaulted ctor param: unlike the repository it has
    no protocol to serve as a DI key, and its production path is already lazy —
    ``_build_qdrant_client()`` is called inside ``handle()`` from env config
    whenever the param is ``None``. A default-valued param does not affect boot
    resolvability.

    ``handle()`` takes a single typed ``ModelCodeEmbeddingRequest`` payload and
    returns a single typed model (definition-B) — no envelope, no coercion; the
    runtime wraps. That signature is unchanged by this refactor.
    """

    def __init__(
        self,
        container: ModelONEXContainer,
        qdrant_client: Any | None = None,
    ) -> None:
        self._container = container
        self._qdrant_client = qdrant_client

    def _resolve_repository(self) -> ProtocolCodeEntityRepository:
        """Resolve ProtocolCodeEntityRepository from the container.

        Called at the effect boundary inside ``handle()``, never at
        construction. Fails loud when no provider is registered.
        """
        # NOTE(OMN-13603): mypy false-positive — a Protocol is the canonical DI
        # key for get_service; it is never instantiated here.
        return self._container.get_service(
            ProtocolCodeEntityRepository  # type: ignore[type-abstract]  # Protocol used as DI key
        )

    async def handle(
        self, payload: ModelCodeEmbeddingRequest
    ) -> ModelCodeEmbeddingResult:
        """Embed a batch of code entities and upsert into Qdrant."""
        correlation_id = payload.correlation_id
        endpoint = (
            payload.embedding_endpoint_override
            or os.environ.get(  # contract-config-ok: config
                "EMBEDDING_MODEL_URL", ""
            )
        )
        if not endpoint:
            raise OSError(
                "EMBEDDING_MODEL_URL is required but not set. "
                "Set this env var to the OpenAI-compatible embedding endpoint base URL."
            )

        collection = (
            payload.qdrant_collection_override
            or os.environ.get(  # contract-config-ok: config
                "QDRANT_CODE_COLLECTION", DEFAULT_QDRANT_COLLECTION
            )
        )
        # batch_size <= 0 is rejected at payload construction (Field(gt=0) on
        # ModelCodeEmbeddingRequest) — no manual re-validation needed here.
        effective_batch_size = (
            payload.batch_size
            if payload.batch_size is not None
            else int(
                os.environ.get(  # contract-config-ok: config
                    "CODE_EMBEDDING_BATCH_SIZE", str(DEFAULT_EMBEDDING_BATCH_SIZE)
                )
            )
        )
        vector_size = int(
            os.environ.get(  # contract-config-ok: config
                "CODE_EMBEDDING_VECTOR_SIZE", str(DEFAULT_VECTOR_SIZE)
            )
        )

        resolved_client = self._qdrant_client
        if resolved_client is None:
            resolved_client = _build_qdrant_client()
            if resolved_client is None:
                logger.warning(
                    "Qdrant unavailable — skipping embedding batch (correlation_id=%s)",
                    correlation_id,
                )
                return ModelCodeEmbeddingResult(
                    correlation_id=correlation_id,
                    embedded_count=0,
                    failed_count=0,
                    qdrant_collection=collection,
                    batch_size_used=effective_batch_size,
                )

        try:
            _ensure_collection(resolved_client, collection, vector_size)
        except Exception:
            logger.exception(
                "Qdrant collection setup failed — skipping embedding batch (correlation_id=%s)",
                correlation_id,
            )
            return ModelCodeEmbeddingResult(
                correlation_id=correlation_id,
                embedded_count=0,
                failed_count=0,
                qdrant_collection=collection,
                batch_size_used=effective_batch_size,
            )

        # Effect boundary: resolve the repository at first use, after the
        # Qdrant graceful-skip paths above, so an unavailable Qdrant still
        # short-circuits without demanding a provider (module invariant).
        repository = self._resolve_repository()

        entities = await repository.get_entities_needing_embedding(
            limit=effective_batch_size
        )
        if not entities:
            logger.info(
                "No entities needing embedding (correlation_id=%s)", correlation_id
            )
            return ModelCodeEmbeddingResult(
                correlation_id=correlation_id,
                embedded_count=0,
                failed_count=0,
                qdrant_collection=collection,
                batch_size_used=effective_batch_size,
            )

        embedded_ids: list[str] = []
        failed = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            for entity in entities:
                try:
                    text = build_embedding_text(entity)
                    if not text.strip():
                        failed += 1
                        continue

                    embedding = await _get_embedding(client, endpoint, text)
                    if embedding is None:
                        failed += 1
                        continue

                    _upsert_point(resolved_client, collection, entity, embedding)
                    embedded_ids.append(str(entity["id"]))
                except Exception:
                    logger.exception(
                        "Failed to embed entity %s (correlation_id=%s)",
                        entity.get("entity_name"),
                        correlation_id,
                    )
                    failed += 1

        if embedded_ids:
            await repository.update_embedded_at(embedded_ids)

        logger.info(
            "Embedding complete: %d embedded, %d failed (correlation_id=%s)",
            len(embedded_ids),
            failed,
            correlation_id,
        )
        return ModelCodeEmbeddingResult(
            correlation_id=correlation_id,
            embedded_count=len(embedded_ids),
            failed_count=failed,
            vector_ids=embedded_ids,
            qdrant_collection=collection,
            batch_size_used=effective_batch_size,
        )


def build_embedding_text(entity: dict[str, Any]) -> str:
    """Build embedding text using tiered fields.

    Primary fields (source-derived, stable) are always included.
    Secondary fields (LLM-generated) are appended after a newline if available.
    """
    parts: list[str] = []
    if entity.get("entity_name"):
        parts.append(entity["entity_name"])
    if entity.get("signature"):
        parts.append(entity["signature"])
    if entity.get("docstring"):
        parts.append(entity["docstring"])

    primary_text = " ".join(parts)

    secondary_parts: list[str] = []
    if entity.get("llm_description"):
        secondary_parts.append(entity["llm_description"])

    if secondary_parts:
        return f"{primary_text}\n{' '.join(secondary_parts)}"
    return primary_text


def _build_qdrant_client() -> Any | None:
    """Build QdrantClient from env vars.

    Returns None only when qdrant-client is not installed or QDRANT_HOST is unset.
    Raises on connection failures so bad config is never silently swallowed.
    """
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        logger.info("qdrant-client not installed; embedding pipeline will be a no-op")
        return None

    host = os.environ.get(  # contract-config-ok: config
        "QDRANT_HOST"
    )
    if not host:
        logger.info("QDRANT_HOST not set; embedding pipeline will be a no-op")
        return None

    port = int(
        os.environ.get("QDRANT_PORT", "6333")  # contract-config-ok: config
    )
    client = QdrantClient(host=host, port=port)
    client.get_collections()  # connectivity probe — raises on auth/network failure
    return client


def _ensure_collection(client: Any, collection: str, vector_size: int) -> None:
    """Create Qdrant collection if it does not exist.

    Raises on unexpected errors so bad config is surfaced, not swallowed.
    Only suppresses the trivial "already exists" race condition.
    """
    from qdrant_client.models import Distance, VectorParams

    existing = [c.name for c in client.get_collections().collections]
    if collection not in existing:
        try:
            client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info(
                "Created Qdrant collection: %s (dim=%d)", collection, vector_size
            )
        except Exception:
            # Re-check — another worker may have created it concurrently
            existing_after = [c.name for c in client.get_collections().collections]
            if collection not in existing_after:
                logger.exception("Failed to create Qdrant collection %s", collection)
                raise


def _upsert_point(
    client: Any, collection: str, entity: dict[str, Any], embedding: list[float]
) -> None:
    from qdrant_client.models import PointStruct

    point = PointStruct(
        id=str(entity["id"]),
        vector=embedding,
        payload={
            "entity_id": str(entity["id"]),
            "entity_name": entity.get("entity_name", ""),
            "entity_type": entity.get("entity_type", ""),
            "qualified_name": entity.get("qualified_name", ""),
            "source_repo": entity.get("source_repo", ""),
            "source_path": entity.get("source_path", ""),
            "classification": entity.get("classification"),
            "docstring": (entity.get("docstring") or "")[:200],
        },
    )
    client.upsert(collection_name=collection, points=[point])


async def _get_embedding(
    client: httpx.AsyncClient,
    endpoint: str,
    text: str,
) -> list[float] | None:
    try:
        response = await client.post(
            f"{endpoint}/v1/embeddings",
            json={"input": text, "model": "embedding"},
        )
        response.raise_for_status()
        data = response.json()
        embedding: list[float] = data["data"][0]["embedding"]
        return embedding
    except (httpx.HTTPError, KeyError, IndexError):
        logger.warning("Embedding generation failed for endpoint=%r", endpoint)
        return None


__all__ = [
    "HandlerCodeEmbeddingEffect",
    # Re-exported (OMN-15230): the canonical declaration lives in
    # omnimarket.protocols; existing importers of this module keep resolving the
    # same class object, which is the whole point of the consolidation.
    "ProtocolCodeEntityRepository",
    "build_embedding_text",
]

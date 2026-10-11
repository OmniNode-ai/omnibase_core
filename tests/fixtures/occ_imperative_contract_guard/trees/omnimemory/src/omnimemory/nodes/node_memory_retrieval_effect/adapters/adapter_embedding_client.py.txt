# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""Async embedding client for MLX embedding server.

MLX Qwen3-Embedding server. The client supports connection pooling, automatic
retries with exponential backoff, and configurable timeouts.

The MLX server provides high-performance embeddings with ~1.3ms latency and
produces 1024-dimensional vectors suitable for semantic similarity search.

Example::

    import asyncio
    import os
    from omnimemory.nodes.node_memory_retrieval_effect.adapters import (
        EmbeddingClient,
        ModelEmbeddingClientConfig,
    )

    async def example():
        # URL must be provided explicitly (from environment variable)
        embedding_url = os.environ["OMNIMEMORY__EMBEDDING__SERVER_URL"]  # url-authority-ok: docstring example for legacy env-supplied embedding endpoint, OMN-2584
        config = ModelEmbeddingClientConfig(base_url=embedding_url)
        client = EmbeddingClient(config)

        async with client:
            embedding = await client.get_embedding("Hello world")
            print(f"Embedding dimension: {len(embedding)}")
            print(f"First 5 values: {embedding[:5]}")

    asyncio.run(example())

.. versionadded:: 0.1.0
    Initial implementation for OMN-1387.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import httpx  # transport-import-ok node-purity-ok: effect-node embedding client httpx (designated I/O boundary), OMN-13283

if TYPE_CHECKING:
    from types import TracebackType

from ..models import ModelEmbeddingClientConfig

logger = logging.getLogger(__name__)

# HTTP status code ranges for error classification
HTTP_CLIENT_ERROR_MIN = 400
HTTP_CLIENT_ERROR_MAX = 500  # Exclusive upper bound for client errors (4xx range)

__all__ = [
    "EmbeddingClient",
    "ModelEmbeddingClientConfig",
    "EmbeddingClientError",
    "EmbeddingConnectionError",
    "EmbeddingTimeoutError",
]


class EmbeddingClientError(Exception):
    """Base exception for embedding client errors."""


class EmbeddingConnectionError(EmbeddingClientError):
    """Raised when connection to embedding server fails."""


class EmbeddingTimeoutError(EmbeddingClientError):
    """Raised when embedding request times out."""


class EmbeddingClient:
    """Async client for MLX embedding server with connection pooling.

    This client provides efficient embedding generation through connection
    pooling and automatic retry handling. It supports both context manager
    and manual lifecycle management.

    The client maintains a persistent httpx.AsyncClient for connection reuse,
    which significantly improves performance for batch embedding operations.

    Attributes:
        config: The client configuration.

    Example using context manager::

        import os
        embedding_url = os.environ["OMNIMEMORY__EMBEDDING__SERVER_URL"]  # url-authority-ok: docstring example for legacy env-supplied embedding endpoint, OMN-2584
        config = ModelEmbeddingClientConfig(base_url=embedding_url)
        client = EmbeddingClient(config)

        async with client:
            # Connection pool is active
            emb1 = await client.get_embedding("First text")
            emb2 = await client.get_embedding("Second text")
        # Connection pool is closed

    Example using manual lifecycle::

        import os
        embedding_url = os.environ["OMNIMEMORY__EMBEDDING__SERVER_URL"]  # url-authority-ok: docstring example for legacy env-supplied embedding endpoint, OMN-2584
        config = ModelEmbeddingClientConfig(base_url=embedding_url)
        client = EmbeddingClient(config)
        await client.connect()
        try:
            embedding = await client.get_embedding("Hello")
        finally:
            await client.close()
    """

    def __init__(self, config: ModelEmbeddingClientConfig) -> None:
        """Initialize the embedding client.

        Args:
            config: Client configuration (REQUIRED - base_url must be provided).
        """
        self._config = config
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    @property
    def config(self) -> ModelEmbeddingClientConfig:
        """Get the client configuration."""
        return self._config

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected with an active connection pool."""
        return self._connected and self._client is not None

    @property
    def embed_url(self) -> str:
        """Get the full URL for the embed endpoint."""
        base = self._config.base_url.rstrip("/")
        return f"{base}/embed"

    async def connect(self) -> None:
        """Establish connection pool to the embedding server.

        Creates an httpx.AsyncClient with connection pooling enabled.
        Safe to call multiple times - subsequent calls are no-ops.
        """
        if self._connected:
            return

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._config.timeout_seconds),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
            ),
        )
        self._connected = True
        logger.debug(
            "Embedding client connected to %s",
            self._config.base_url,
        )

    async def close(self) -> None:
        """Close the connection pool and release resources.

        Safe to call multiple times - subsequent calls are no-ops.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._connected = False
        logger.debug("Embedding client connection closed")

    async def __aenter__(self) -> EmbeddingClient:
        """Enter async context manager."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.close()

    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for the given text.

        Sends a POST request to the MLX embedding server and returns the
        resulting embedding vector. Automatically retries on transient
        failures with exponential backoff.

        Args:
            text: The text to embed. Should be non-empty.

        Returns:
            A list of floats representing the embedding vector. The dimension
            matches the configured embedding_dimension (default: 1024).

        Raises:
            EmbeddingClientError: If text is empty or response is invalid.
            EmbeddingConnectionError: If connection to server fails after
                all retries are exhausted.
            EmbeddingTimeoutError: If request times out after all retries.

        Example::

            import os
            embedding_url = os.environ["OMNIMEMORY__EMBEDDING__SERVER_URL"]  # url-authority-ok: docstring example for legacy env-supplied embedding endpoint, OMN-2584
            config = ModelEmbeddingClientConfig(base_url=embedding_url)
            async with EmbeddingClient(config) as client:
                embedding = await client.get_embedding("Hello world")
                assert len(embedding) == 1024
        """
        if not text or not text.strip():
            raise EmbeddingClientError("Text cannot be empty")

        # Ensure connected
        if not self._connected:
            await self.connect()

        last_exception: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                return await self._execute_request(text)

            except httpx.TimeoutException as e:
                last_exception = EmbeddingTimeoutError(
                    f"Embedding timeout after {self._config.timeout_seconds}s: {e}"
                )
                logger.warning(
                    "Embedding request timeout (attempt %d/%d): %s",
                    attempt + 1,
                    self._config.max_retries + 1,
                    e,
                )

            except httpx.ConnectError as e:
                last_exception = EmbeddingConnectionError(
                    f"Connection failed to {self._config.base_url}: {e}"
                )
                logger.warning(
                    "Embedding connection error (attempt %d/%d): %s",
                    attempt + 1,
                    self._config.max_retries + 1,
                    e,
                )

            except httpx.HTTPStatusError as e:
                # Don't retry on client errors (4xx)
                if (
                    HTTP_CLIENT_ERROR_MIN
                    <= e.response.status_code
                    < HTTP_CLIENT_ERROR_MAX
                ):
                    raise EmbeddingClientError(
                        f"Embedding server returned client error: "
                        f"{e.response.status_code} - {e.response.text}"
                    ) from e

                last_exception = EmbeddingClientError(
                    f"Embedding server error: {e.response.status_code}"
                )
                logger.warning(
                    "Embedding server error (attempt %d/%d): %s",
                    attempt + 1,
                    self._config.max_retries + 1,
                    e,
                )

            # Exponential backoff before retry (skip on last attempt)
            if attempt < self._config.max_retries:
                delay = self._config.retry_base_delay * (2**attempt)
                logger.debug("Retrying in %.2f seconds...", delay)
                await asyncio.sleep(delay)

        # All retries exhausted
        if last_exception is not None:
            raise last_exception

        raise EmbeddingClientError("Unexpected error: no exception captured")

    async def _execute_request(self, text: str) -> list[float]:
        """Execute the embedding request.

        Args:
            text: The text to embed.

        Returns:
            The embedding vector.

        Raises:
            EmbeddingClientError: If response format is invalid.
            httpx.HTTPStatusError: If server returns error status.
            httpx.TimeoutException: If request times out.
            httpx.ConnectError: If connection fails.
        """
        if self._client is None:
            raise EmbeddingClientError("Client not connected")

        response = await self._client.post(
            self.embed_url,
            json={"text": text},
        )
        response.raise_for_status()

        data = response.json()

        # Handle different response formats
        embedding: list[float]
        if isinstance(data, list):
            # Direct list response
            embedding = data
        elif isinstance(data, dict) and "embedding" in data:
            # Wrapped response: {"embedding": [...]}
            embedding = data["embedding"]
        else:
            raise EmbeddingClientError(
                f"Unexpected response format from embedding server: {type(data)}"
            )

        # Validate embedding
        if not isinstance(embedding, list):
            raise EmbeddingClientError(
                f"Expected list for embedding, got {type(embedding)}"
            )

        if len(embedding) != self._config.embedding_dimension:
            logger.warning(
                "Embedding dimension mismatch: expected %d, got %d",
                self._config.embedding_dimension,
                len(embedding),
            )

        return embedding

    async def get_embeddings_batch(
        self,
        texts: list[str],
        max_concurrency: int = 5,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts concurrently.

        Processes multiple texts in parallel with controlled concurrency
        to avoid overwhelming the embedding server.

        Args:
            texts: List of texts to embed.
            max_concurrency: Maximum number of concurrent requests.

        Returns:
            List of embedding vectors in the same order as input texts.

        Raises:
            EmbeddingClientError: If any text fails to embed.

        Example::

            import os
            embedding_url = os.environ["OMNIMEMORY__EMBEDDING__SERVER_URL"]  # url-authority-ok: docstring example for legacy env-supplied embedding endpoint, OMN-2584
            config = ModelEmbeddingClientConfig(base_url=embedding_url)
            async with EmbeddingClient(config) as client:
                texts = ["Hello", "World", "Test"]
                embeddings = await client.get_embeddings_batch(texts)
                assert len(embeddings) == 3
        """
        if not texts:
            return []

        # Ensure connected
        if not self._connected:
            await self.connect()

        semaphore = asyncio.Semaphore(max_concurrency)

        async def embed_with_semaphore(text: str) -> list[float]:
            async with semaphore:
                return await self.get_embedding(text)

        tasks = [embed_with_semaphore(text) for text in texts]
        return await asyncio.gather(*tasks)

    async def health_check(self) -> bool:
        """Check if the embedding server is reachable and responding.

        Attempts to generate an embedding for a simple test string.

        Returns:
            True if server is healthy, False otherwise.

        Example::

            import os
            embedding_url = os.environ["OMNIMEMORY__EMBEDDING__SERVER_URL"]  # url-authority-ok: docstring example for legacy env-supplied embedding endpoint, OMN-2584
            config = ModelEmbeddingClientConfig(base_url=embedding_url)
            client = EmbeddingClient(config)
            async with client:
                if await client.health_check():
                    print("Server is healthy")
        """
        try:
            await self.get_embedding("health check")
            return True
        except EmbeddingClientError:
            return False

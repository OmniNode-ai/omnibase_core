# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HTTP client for the kreuzberg document extraction REST service.

This module is the designated transport boundary for kreuzberg HTTP calls.
All httpx usage is confined here per ARCH-002.

.. versionadded:: 0.5.0
    Initial implementation for OMN-2733.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx  # transport-import-ok node-purity-ok: effect-node client httpx (designated I/O boundary), OMN-2733

__all__ = [
    "KreuzbergExtractionError",
    "KreuzbergTimeoutError",
    "call_kreuzberg_extract",
    "read_cached_text",
    "write_cached_text",
]

# Prefix written as the first line of every cached text file.
# Both read_cached_text and write_cached_text rely on this exact string; keeping
# it at module level ensures they can never silently diverge.
_FINGERPRINT_PREFIX = "fingerprint:"


class KreuzbergTimeoutError(Exception):
    """Raised when the kreuzberg /extract request exceeds the configured timeout."""


class KreuzbergExtractionError(Exception):
    """Raised when kreuzberg returns a non-2xx HTTP response."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class KreuzbergExtractResult:
    """Result from a successful kreuzberg /extract call."""

    extracted_text: str
    status: Literal["ok"] = "ok"


async def call_kreuzberg_extract(
    *,
    kreuzberg_url: str,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    timeout_seconds: float,
) -> KreuzbergExtractResult:
    """Call kreuzberg POST /extract and return the extracted text.

    Args:
        kreuzberg_url: Base URL of the kreuzberg service
            (e.g. ``"http://localhost:8090"``).  # url-authority-ok: doc example for caller-provided local kreuzberg endpoint
        file_bytes: Raw binary content of the document to parse.
        filename: Original filename hint for kreuzberg (e.g. ``"report.pdf"``).
        mime_type: MIME type hint for kreuzberg.
        timeout_seconds: Request timeout in seconds.

    Returns:
        KreuzbergExtractResult with the extracted plain text.

    Raises:
        KreuzbergTimeoutError: If the request exceeds ``timeout_seconds``.
        KreuzbergExtractionError: If kreuzberg returns a non-2xx response,
            a transport-level failure occurs, or a request-side error such as
            ``httpx.TooManyRedirects`` or ``httpx.InvalidURL`` is raised.
    """
    extract_url = f"{kreuzberg_url.rstrip('/')}/extract"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds)) as client:
            response = await client.post(
                extract_url,
                files=[("files", (filename, file_bytes, mime_type))],
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise KreuzbergTimeoutError(
            f"kreuzberg extract timed out after {timeout_seconds:.1f}s"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise KreuzbergExtractionError(
            status_code=exc.response.status_code,
            detail=exc.response.text[:200],
        ) from exc
    except httpx.TransportError as exc:
        raise KreuzbergExtractionError(
            status_code=503,
            detail=f"kreuzberg transport error: {exc}",
        ) from exc
    except httpx.RequestError as exc:
        raise KreuzbergExtractionError(
            status_code=503,
            detail=f"kreuzberg request error: {exc}",
        ) from exc

    try:
        response_data = response.json()
    except (ValueError, httpx.DecodingError) as exc:
        raise KreuzbergExtractionError(
            status_code=response.status_code,
            detail=f"kreuzberg returned non-JSON response: {exc}",
        ) from exc
    if not isinstance(response_data, list):
        raise KreuzbergExtractionError(
            status_code=200,
            detail=f"kreuzberg returned unexpected response type: {type(response_data).__name__}",
        )
    if not response_data:
        raise KreuzbergExtractionError(
            status_code=200,
            detail="kreuzberg returned empty response array",
        )
    try:
        content = response_data[0]["content"]
    except (KeyError, TypeError):
        raise KreuzbergExtractionError(
            status_code=200,
            detail="kreuzberg response item has unexpected format",
        )
    if content is None:
        raise KreuzbergExtractionError(
            status_code=200,
            detail="kreuzberg returned null content",
        )

    return KreuzbergExtractResult(extracted_text=str(content))


def read_cached_text(text_path: Path) -> tuple[str, str] | None:
    """Read cached text file and return (fingerprint, text) if available.

    The file format is::

        fingerprint:<sha256_hex>\\n
        <extracted_text>

    Returns None if the file does not exist or cannot be parsed.
    """
    if not text_path.exists():
        return None
    try:
        content = text_path.read_text(  # node-purity-ok: effect-node client idempotency cache read (designated I/O boundary), OMN-2733
            encoding="utf-8"
        )
        first_newline = content.index("\n")
        first_line = content[:first_newline]
        if not first_line.startswith(_FINGERPRINT_PREFIX):
            return None
        stored_fingerprint = first_line[len(_FINGERPRINT_PREFIX) :]
        text = content[first_newline + 1 :]
        return stored_fingerprint, text
    except (OSError, ValueError):
        return None


def write_cached_text(text_path: Path, fingerprint: str, text: str) -> None:
    """Write extracted text to the text store file.

    Args:
        text_path: Destination path for the cached text file.
        fingerprint: SHA-256 hex fingerprint of the source document content.
        text: Extracted text content to store.
    """
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(  # node-purity-ok: effect-node client idempotency cache write (designated I/O boundary), OMN-2733
        f"{_FINGERPRINT_PREFIX}{fingerprint}\n{text}",
        encoding="utf-8",
    )

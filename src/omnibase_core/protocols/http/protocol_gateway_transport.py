# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""POST seam for the ``onex auth`` gateway client (OMN-15922).

ARCHITECTURE BOUNDARY (ADR-005) — read before implementing against this.
    ``omnibase_core`` may not import a transport library at runtime; the
    ``validate-no-transport-imports`` gate enforces it over the whole package.
    So the credential store, the token minter, the renewal planner and the
    session client all live here as pure logic over THIS protocol, and the one
    concrete adapter that actually opens a socket (httpx/aiohttp) belongs in
    ``omnibase_infra``. That is the same split ``ProtocolHttpClient`` already
    documents for GET.

Why a second protocol rather than adding ``post`` to ``ProtocolHttpClient``:
    ``ProtocolHttpClient`` is ``@runtime_checkable`` and is already satisfied
    structurally by adapters that implement exactly ``get``. Adding a method
    would silently un-satisfy every one of them -- a breaking change to an
    existing seam, in service of a new caller. The two POST shapes this client
    needs are also genuinely different from that protocol's concern: an OAuth2
    token endpoint takes ``application/x-www-form-urlencoded`` (RFC 6749 §2.3.1)
    and the gateway takes JSON, and collapsing them into one ``post(body)``
    would push content-type assembly into every caller.

Both methods return ``ProtocolHttpResponse`` -- the response seam already
defined next door -- so an implementation reuses whatever adapter it has.
Callers here read ``status`` and ``text()`` only, never ``json()``: the bodies
are parsed through typed Pydantic models, so an ``Any``-returning hop would
throw away the typing the models exist to provide.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from omnibase_core.protocols.http.protocol_http_client import ProtocolHttpResponse

__all__ = ["ProtocolGatewayTransport"]


@runtime_checkable
class ProtocolGatewayTransport(Protocol):
    """Async POST transport for the token endpoint and the gateway."""

    async def post_form(
        self,
        url: str,
        *,
        form: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> ProtocolHttpResponse:
        """POST ``form`` as ``application/x-www-form-urlencoded``.

        Used for the OAuth2 ``client_credentials`` grant. Implementations MUST
        NOT log the form -- it carries ``client_secret``.

        Args:
            url: Absolute token-endpoint URL.
            form: Form fields to url-encode as the request body.
            headers: Headers to send; the implementation owns Content-Type.

        Returns:
            The response, with status and body available for the caller to
            classify. Implementations must not raise on non-2xx -- fail-closed
            classification is the caller's, and it needs the status to say
            anything useful about it.
        """
        ...

    async def post_json(
        self,
        url: str,
        *,
        body: str,
        headers: Mapping[str, str],
    ) -> ProtocolHttpResponse:
        """POST an already-serialized JSON ``body``.

        The body arrives serialized rather than as a mapping so the caller's
        Pydantic model stays the single authority on the wire shape (field
        order, datetime encoding, alias handling) instead of that being
        re-decided by whichever JSON encoder the adapter happens to use.

        Args:
            url: Absolute gateway URL.
            body: Serialized JSON request body.
            headers: Headers to send, including ``Authorization``.

        Returns:
            The response, unclassified — see ``post_form``.
        """
        ...

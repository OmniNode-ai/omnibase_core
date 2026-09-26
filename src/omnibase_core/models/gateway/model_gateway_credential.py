# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelGatewayCredential — one tenant's machine identity for the gateway (OMN-15922).

The resolved form of what ``~/.onex`` holds: the per-tenant confidential
Keycloak client (``client_credentials`` grant, ``clientId`` == the immutable
``principal_id``) plus the two contract-supplied URLs it is used against.

``client_secret`` is a ``SecretStr`` deliberately. This model is constructed on
the CLI path, passed into services, and therefore ends up inside tracebacks,
``repr()`` output and structured log records whenever anything downstream
raises. ``SecretStr`` renders as ``**********`` in every one of those, which is
the only reason a plain-string field would ever have been "fine until it
wasn't". Read the value only where it is about to go on the wire, via
``get_secret_value()``.

No field here is optional. A half-configured credential is exactly the state
that produces an anonymous call the operator believes is authenticated, so
absence is resolved (and refused) at the store boundary, never represented.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr

__all__ = ["ModelGatewayCredential"]


class ModelGatewayCredential(BaseModel):
    """A tenant's client-credentials identity plus its resolved endpoints."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tenant_slug: str = Field(min_length=1)
    # Keycloak clientId of the per-tenant confidential client. This IS the
    # principal_id the gateway resolves authority from -- it is not a label.
    client_id: str = Field(min_length=1)
    client_secret: SecretStr
    # Realm token endpoint, supplied by configuration rather than assembled
    # from a hardcoded issuer -- the realm differs per tenant.
    token_endpoint: str = Field(min_length=1)
    # Gateway origin the attach/heartbeat paths are appended to.
    base_url: str = Field(min_length=1)
    # Caller-declared host label, used by the gateway for session bookkeeping
    # only -- never for authorization, which comes from the token claims.
    edge_instance_id: str = Field(min_length=1, max_length=255)

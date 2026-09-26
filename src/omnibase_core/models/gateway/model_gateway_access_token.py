# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelGatewayAccessToken — one minted client-credentials token (OMN-15922).

``expires_at`` is absolute, derived once from the grant's ``expires_in`` at the
instant of the grant. Carrying the relative form instead would push the "when
does this die" arithmetic to every call site, and each of those would have to
remember which instant it was relative to.

``audiences`` is the normalised ``aud`` claim as a SET. RFC 7519 4.1.3 permits
``aud`` to be a single string or an array, and Keycloak emits the array form as
soon as a client carries more than one audience mapper -- so multiplicity and
order must not be observable to anything downstream. The gateway compares the
set for exact equality against ``{"gateway-attach"}``; this field is what lets
the client apply the identical comparison before the token is ever used.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = ["ModelGatewayAccessToken"]


class ModelGatewayAccessToken(BaseModel):
    """A minted access token with its absolute expiry and audience set."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # SecretStr for the same reason ModelGatewayCredential.client_secret is:
    # a bearer token in a traceback is a credential in a log aggregator.
    access_token: SecretStr
    expires_at: datetime
    audiences: frozenset[str]

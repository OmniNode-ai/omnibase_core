# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Which credential actually served a delegation call (OMN-18196)."""

from __future__ import annotations

from enum import StrEnum


class EnumCredentialSource(StrEnum):
    """The credential the effect boundary resolved for a provider call.

    Axiom 9 forbids a customer route binding a house credential. A model name
    cannot witness that prohibition, because the same model id is reachable on
    a customer's own key and on a house credential alike. This enum is the
    fact itself, and it is only ever produced by the boundary that resolved
    the credential for the call — never inferred downstream from a model, a
    route, a tier name, or a tenant's configuration read after the fact.

    ``NONE`` is a real outcome, not an absence: the call reached the provider
    with no credential attached. It is distinct from the field being unset on
    a terminal emitted before this field existed, which stays ``None``.

    A tenant whose registered credential was withdrawn keeps its routing
    overlay row with a blanked ``secret_ref`` (OMN-18191), so the binding it
    resolves to carries no reference. That case classifies as ``NONE``. It
    must never read as ``CUSTOMER_KEY``: the row still names the customer, but
    no customer credential answered.
    """

    CUSTOMER_KEY = "customer_key"
    HOUSE = "house"
    NONE = "none"


__all__ = ["EnumCredentialSource"]

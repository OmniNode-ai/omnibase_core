# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cost-and-locality class of a catalogued model (OMN-19391).

The ``llm.catalog`` overlay carries this per model so that no consumer (a
dashboard, a staging bar, a router) classifies a model from its name.

Three members, as plan section 3.1 declares them. A free hosted model (plan
task D3's free frontier list) is ``CHEAP_CLOUD`` with the catalog entry's
``free`` flag set: whether a model costs anything is a price fact, carried once
by that flag, not a fourth tier.
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumLlmTierClass(StrEnum):
    """Tier class of a model in the ``llm.catalog`` overlay."""

    LOCAL = "local"
    """Served on hardware the operator runs."""

    CHEAP_CLOUD = "cheap_cloud"
    """Hosted by a vendor at a low or zero per-token price."""

    FRONTIER = "frontier"
    """A hosted frontier model at a premium per-token price."""


__all__ = ["EnumLlmTierClass"]

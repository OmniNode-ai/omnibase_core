# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Content kind discriminator for omniweb-v2 landing page sections."""

from enum import StrEnum


class EnumContentKind(StrEnum):
    """Discriminator for content payload data shape. One value per landing page section."""

    HERO = "hero"
    TRUST = "trust"
    NODE_CATALOG = "node_catalog"
    EXECUTION_GRAPH = "execution_graph"
    EVENT_STREAM = "event_stream"
    CONTRACT_YAML = "contract_yaml"
    OPEN_CORE = "open_core"
    CTA = "cta"
    FOOTER = "footer"

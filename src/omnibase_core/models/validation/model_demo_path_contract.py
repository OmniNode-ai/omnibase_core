# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Parsed data for a single demo-path node contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelDemoPathContract:
    """Parsed representation of a single demo-path contract.yaml."""

    name: str
    contract_path: Path
    subscribe_topics: frozenset[str]
    publish_topics: frozenset[str]
    widget_topics: frozenset[str]


__all__ = ["ModelDemoPathContract"]

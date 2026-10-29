# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCheckerRuleDataModuleFact — one Python module as the K10 checker reads it (OMN-21503)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelCheckerRuleDataModuleFact:
    """One Python module: its file name, source and the names that sit beside it."""

    name: str
    posix_path: str
    source: str
    sibling_names: frozenset[str]
    contract_names: frozenset[str]

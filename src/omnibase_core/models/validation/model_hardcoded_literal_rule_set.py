# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelHardcodedLiteralRuleSet -- the rule rows of K6 families O, G, F, P, S, H and B (OMN-21537)."""

from __future__ import annotations

from dataclasses import dataclass

from omnibase_core.models.validation.model_hardcoded_literal_rule_row import (
    ModelHardcodedLiteralRuleRow,
)


@dataclass(frozen=True, slots=True)
class ModelHardcodedLiteralRuleSet:
    """Every vocabulary the literal families judge, read from the validator contract.

    ``rows`` holds the enabled rule rows only. The other fields are the typed
    ``parameters`` of the rows plus the three facts a repository supplies
    (``g_org``, ``p_names``, ``h_host_names``), none of which the checker spells.
    """

    rows: tuple[ModelHardcodedLiteralRuleRow, ...]
    o_name_patterns: tuple[str, ...]
    o_call_names: tuple[str, ...]
    o_min_value: int
    o_text_patterns: tuple[str, ...]
    g_hosts: tuple[str, ...]
    g_scheme_patterns: tuple[str, ...]
    g_placeholder_pattern: str
    g_org: str
    f_home_calls: tuple[str, ...]
    f_parameter_name_patterns: tuple[str, ...]
    f_dot_directory_pattern: str
    f_constant_name_patterns: tuple[str, ...]
    f_anchor_names: tuple[str, ...]
    f_path_constructors: tuple[str, ...]
    p_names: tuple[str, ...]
    p_min_members: int
    s_stamp_pattern: str
    s_text_pattern: str
    h_host_names: tuple[str, ...]
    h_min_members: int
    b_name_patterns: tuple[str, ...]
    b_min_value: int
    b_text_pattern: str
    python_suffixes: tuple[str, ...]
    slash_comment_suffixes: tuple[str, ...]
    no_comment_suffixes: tuple[str, ...]
    exclude_patterns: tuple[str, ...] = ()

    def families(self) -> frozenset[str]:
        """The families whose rule row is enabled."""
        return frozenset(row.family for row in self.rows)


__all__ = ["ModelHardcodedLiteralRuleSet"]

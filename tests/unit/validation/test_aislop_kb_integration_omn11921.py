# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TDD tests for OMN-11921: aislop validator KB integration.

Covers:
- resolve_rules_from_registry(): filters registry to regex/grep/ast types, converts to ModelAislopRule
- resolve_rules_unified(): merges legacy aislop defaults + registry; registry wins on duplicate name
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_aislop_rule import ModelAislopRule
from omnibase_core.models.validation.model_aislop_rule_set import ModelAislopRuleSet
from omnibase_core.validation.aislop_rule_loader import (
    load_default_rules,
    resolve_rules_from_registry,
    resolve_rules_unified,
)
from omnibase_core.validation.antipattern_registry_loader import (
    load_default_antipatterns,
)

# ---------------------------------------------------------------------------
# resolve_rules_from_registry
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveRulesFromRegistry:
    def test_returns_rule_set(self) -> None:
        registry = load_default_antipatterns()
        result = resolve_rules_from_registry(registry)
        assert isinstance(result, ModelAislopRuleSet)

    def test_all_rules_are_model_aislop_rule(self) -> None:
        registry = load_default_antipatterns()
        result = resolve_rules_from_registry(registry)
        for rule in result.rules:
            assert isinstance(rule, ModelAislopRule)

    def test_excludes_semantic_entries(self) -> None:
        registry = load_default_antipatterns()
        semantic_names = {
            e.name for e in registry.entries if e.pattern_type == "semantic"
        }
        result = resolve_rules_from_registry(registry)
        rule_names = {r.name for r in result.rules}
        assert not semantic_names.intersection(rule_names), (
            f"Semantic entries must be excluded: {semantic_names.intersection(rule_names)}"
        )

    def test_includes_regex_line_entries(self) -> None:
        registry = load_default_antipatterns()
        regex_names = {
            e.name for e in registry.entries if e.pattern_type == "regex_line"
        }
        result = resolve_rules_from_registry(registry)
        rule_names = {r.name for r in result.rules}
        assert regex_names.issubset(rule_names), (
            f"regex_line entries missing: {regex_names - rule_names}"
        )

    def test_includes_grep_code_entries(self) -> None:
        registry = load_default_antipatterns()
        grep_names = {e.name for e in registry.entries if e.pattern_type == "grep_code"}
        result = resolve_rules_from_registry(registry)
        rule_names = {r.name for r in result.rules}
        assert grep_names.issubset(rule_names), (
            f"grep_code entries missing: {grep_names - rule_names}"
        )

    def test_includes_ast_check_entries(self) -> None:
        registry = load_default_antipatterns()
        ast_names = {e.name for e in registry.entries if e.pattern_type == "ast_check"}
        result = resolve_rules_from_registry(registry)
        rule_names = {r.name for r in result.rules}
        assert ast_names.issubset(rule_names)

    def test_converted_rule_fields_match_entry(self) -> None:
        registry = load_default_antipatterns()
        # Find one regex_line or grep_code entry to verify field mapping
        entry = next(
            (
                e
                for e in registry.entries
                if e.pattern_type in ("regex_line", "grep_code")
            ),
            None,
        )
        assert entry is not None, "Expected at least one regex_line or grep_code entry"

        result = resolve_rules_from_registry(registry)
        rule = next((r for r in result.rules if r.name == entry.name), None)
        assert rule is not None
        assert rule.name == entry.name
        assert rule.severity == entry.severity
        assert rule.pattern == entry.pattern
        assert rule.pattern_type == entry.pattern_type
        assert rule.description == entry.description

    def test_file_globs_preserved(self) -> None:
        registry = load_default_antipatterns()
        entry = next(
            (
                e
                for e in registry.entries
                if e.pattern_type in ("regex_line", "grep_code")
            ),
            None,
        )
        assert entry is not None
        result = resolve_rules_from_registry(registry)
        rule = next(r for r in result.rules if r.name == entry.name)
        assert list(rule.file_globs) == list(entry.file_globs)

    def test_empty_registry_returns_empty_rule_set(self) -> None:
        from datetime import datetime

        from omnibase_core.models.validation.model_antipattern_registry import (
            ModelAntipatternRegistry,
        )

        empty = ModelAntipatternRegistry(
            version="0.0.0",
            last_updated=datetime(2026, 1, 1),
            entries=(),
        )
        result = resolve_rules_from_registry(empty)
        assert result.rules == []


# ---------------------------------------------------------------------------
# resolve_rules_unified
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveRulesUnified:
    def test_returns_rule_set(self, tmp_path: Path) -> None:
        result = resolve_rules_unified(tmp_path)
        assert isinstance(result, ModelAislopRuleSet)

    def test_contains_legacy_rules(self, tmp_path: Path) -> None:
        defaults = load_default_rules()
        result = resolve_rules_unified(tmp_path)
        result_names = {r.name for r in result.rules}
        for rule in defaults.rules:
            assert rule.name in result_names, (
                f"Legacy rule '{rule.name}' missing from unified"
            )

    def test_contains_registry_rules(self, tmp_path: Path) -> None:
        registry = load_default_antipatterns()
        registry_rules = resolve_rules_from_registry(registry)
        result = resolve_rules_unified(tmp_path)
        result_names = {r.name for r in result.rules}
        for rule in registry_rules.rules:
            assert rule.name in result_names, (
                f"Registry rule '{rule.name}' missing from unified"
            )

    def test_no_duplicate_names(self, tmp_path: Path) -> None:
        result = resolve_rules_unified(tmp_path)
        names = [r.name for r in result.rules]
        assert len(names) == len(set(names)), (
            f"Duplicate rule names: {[n for n in names if names.count(n) > 1]}"
        )

    def test_registry_wins_on_duplicate_name(self, tmp_path: Path) -> None:
        """When a name exists in both legacy defaults and registry, registry version wins."""
        # sycophancy exists in both legacy aislop defaults and antipattern_registry.yaml
        registry = load_default_antipatterns()
        registry_entry = next(
            (e for e in registry.entries if e.name == "sycophancy"), None
        )
        if registry_entry is None:
            pytest.skip("sycophancy not in registry; cannot test duplicate resolution")

        legacy_defaults = load_default_rules()
        legacy_rule = next(
            (r for r in legacy_defaults.rules if r.name == "sycophancy"), None
        )
        if legacy_rule is None:
            pytest.skip(
                "sycophancy not in legacy defaults; cannot test duplicate resolution"
            )

        result = resolve_rules_unified(tmp_path)
        unified_rule = next(r for r in result.rules if r.name == "sycophancy")

        # The registry version should win — verify at least one field differs or is registry-sourced
        # We prove registry wins by checking the rule matches the registry entry, not the legacy rule
        assert unified_rule.pattern == registry_entry.pattern, (
            "registry version should win on duplicate name 'sycophancy'"
        )

    def test_additive_no_existing_config(self, tmp_path: Path) -> None:
        """Without per-repo config, unified should contain all legacy + all registry rules (minus duplicates)."""
        defaults = load_default_rules()
        registry = load_default_antipatterns()
        registry_rules = resolve_rules_from_registry(registry)

        all_names = {r.name for r in defaults.rules} | {
            r.name for r in registry_rules.rules
        }
        result = resolve_rules_unified(tmp_path)
        result_names = {r.name for r in result.rules}

        assert all_names == result_names, (
            f"Unified missing names: {all_names - result_names}"
        )

    def test_result_rules_are_all_model_aislop_rule(self, tmp_path: Path) -> None:
        result = resolve_rules_unified(tmp_path)
        for rule in result.rules:
            assert isinstance(rule, ModelAislopRule)

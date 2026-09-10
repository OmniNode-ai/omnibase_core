# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for antipattern_registry_loader and default antipattern_registry.yaml (OMN-11911)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

import omnibase_core.validation.antipattern_registry_loader as registry_loader
from omnibase_core.models.validation.model_antipattern_registry import (
    ModelAntipatternRegistry,
)
from omnibase_core.validation.antipattern_registry_loader import (
    load_default_registry,
    load_repo_overrides,
    resolve_antipatterns,
)

# Names of the 17 rules migrated from aislop_default_rules.yaml
_EXPECTED_AISLOP_NAMES = {
    "sycophancy",
    "rest_docstring",
    "boilerplate_docstring",
    "md_separator",
    "step_narration",
    "obvious_comment",
    "hardcoded_ip",
    "hardcoded_localhost",
    "hardcoded_port",
    "hardcoded_topic",
    "prohibited_env_pattern",
    "compat_shim",
    "empty_impl",
    "todo_fixme",
}

# At least these 5 semantic antipatterns must be present
_EXPECTED_SEMANTIC_NAMES = {
    "handler_imports_handler",
    "node_io_in_init",
    "contract_topic_not_in_enum",
    "test_mocks_subject",
    "orchestrator_returns_result",
}


@pytest.mark.unit
class TestLoadDefaultRegistry:
    def test_null_default_registry_preserves_validation_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A bundled null document is not silently treated as an empty registry."""
        (tmp_path / "antipattern_registry.yaml").write_text("null\n", encoding="utf-8")
        monkeypatch.setattr(
            registry_loader.importlib.resources,
            "files",
            lambda _package: tmp_path,
        )

        with pytest.raises(ValidationError):
            load_default_registry()

    def test_invalid_default_registry_preserves_public_validation_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The real typed loader's chained schema failure remains public here."""
        (tmp_path / "antipattern_registry.yaml").write_text(
            "version: '1.0.0'\nentries: []\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            registry_loader.importlib.resources,
            "files",
            lambda _package: tmp_path,
        )

        with pytest.raises(ValidationError, match="last_updated"):
            load_default_registry()

    def test_loads_without_error(self) -> None:
        registry = load_default_registry()
        assert isinstance(registry, ModelAntipatternRegistry)

    def test_version_present(self) -> None:
        registry = load_default_registry()
        assert registry.version != ""

    def test_all_aislop_rules_present(self) -> None:
        registry = load_default_registry()
        names = {e.name for e in registry.entries}
        missing = _EXPECTED_AISLOP_NAMES - names
        assert not missing, f"Missing aislop rules: {missing}"

    def test_all_semantic_antipatterns_present(self) -> None:
        registry = load_default_registry()
        names = {e.name for e in registry.entries}
        missing = _EXPECTED_SEMANTIC_NAMES - names
        assert not missing, f"Missing semantic antipatterns: {missing}"

    def test_semantic_entries_have_vector_enabled(self) -> None:
        registry = load_default_registry()
        semantic = [e for e in registry.entries if e.pattern_type == "semantic"]
        assert len(semantic) >= 5
        for entry in semantic:
            assert entry.vector_enabled, f"{entry.name} must have vector_enabled=True"

    def test_all_entries_have_rationale(self) -> None:
        registry = load_default_registry()
        missing = [e.name for e in registry.entries if not e.rationale.strip()]
        assert not missing, f"Entries missing rationale: {missing}"

    def test_all_entries_have_category(self) -> None:
        registry = load_default_registry()
        for entry in registry.entries:
            assert entry.category in {
                "code_quality",
                "architecture",
                "security",
                "performance",
                "naming",
                "testing",
            }

    def test_yaml_round_trip(self) -> None:
        registry = load_default_registry()
        data = registry.model_dump(mode="json")
        reparsed = ModelAntipatternRegistry.model_validate(data)
        assert len(reparsed.entries) == len(registry.entries)

    @pytest.mark.parametrize(
        ("entry_name", "source"),
        [
            ("obvious_comment", "# TODO: "),
            ("todo_fixme", "# FIXME: resolve this"),
        ],
    )
    def test_unfinished_work_rule_patterns_remain_effective(
        self, entry_name: str, source: str
    ) -> None:
        registry = load_default_registry()
        entry = next(item for item in registry.entries if item.name == entry_name)
        assert re.search(entry.pattern, source) is not None


@pytest.mark.unit
class TestResolveAntipatterns:
    @pytest.mark.parametrize("content", ["null\n", "{}\n"])
    def test_null_or_empty_override_is_an_explicit_empty_override(
        self, tmp_path: Path, content: str
    ) -> None:
        overrides_dir = tmp_path / ".onex"
        overrides_dir.mkdir()
        (overrides_dir / "antipattern-overrides.yaml").write_text(
            content, encoding="utf-8"
        )

        overrides = load_repo_overrides(tmp_path)

        assert overrides is not None
        assert overrides.overrides == []
        assert overrides.custom_entries == []

    def test_invalid_override_preserves_public_validation_error(
        self, tmp_path: Path
    ) -> None:
        overrides_dir = tmp_path / ".onex"
        overrides_dir.mkdir()
        (overrides_dir / "antipattern-overrides.yaml").write_text(
            "unexpected: true\n", encoding="utf-8"
        )

        with pytest.raises(ValidationError, match="unexpected"):
            load_repo_overrides(tmp_path)

    def test_no_overrides_returns_defaults(self, tmp_path: Path) -> None:
        result = resolve_antipatterns(tmp_path)
        defaults = load_default_registry()
        assert len(result.entries) == len(defaults.entries)

    def test_override_severity(self, tmp_path: Path) -> None:
        overrides_dir = tmp_path / ".onex"
        overrides_dir.mkdir()
        overrides_file = overrides_dir / "antipattern-overrides.yaml"
        overrides_file.write_text(
            yaml.dump(
                {
                    "overrides": [
                        {"name": "hardcoded_ip", "severity": "WARNING"},
                    ]
                }
            )
        )
        result = resolve_antipatterns(tmp_path)
        entry = next(e for e in result.entries if e.name == "hardcoded_ip")
        assert entry.severity == "WARNING"

    def test_override_enforcement(self, tmp_path: Path) -> None:
        overrides_dir = tmp_path / ".onex"
        overrides_dir.mkdir()
        overrides_file = overrides_dir / "antipattern-overrides.yaml"
        overrides_file.write_text(
            yaml.dump(
                {
                    "overrides": [
                        {"name": "obvious_comment", "enforcement": "blocking"},
                    ]
                }
            )
        )
        result = resolve_antipatterns(tmp_path)
        entry = next(e for e in result.entries if e.name == "obvious_comment")
        assert entry.enforcement == "blocking"

    def test_unknown_override_name_raises(self, tmp_path: Path) -> None:
        overrides_dir = tmp_path / ".onex"
        overrides_dir.mkdir()
        overrides_file = overrides_dir / "antipattern-overrides.yaml"
        overrides_file.write_text(
            yaml.dump(
                {
                    "overrides": [
                        {"name": "nonexistent_rule", "severity": "ERROR"},
                    ]
                }
            )
        )
        with pytest.raises(ValueError, match="nonexistent_rule"):
            resolve_antipatterns(tmp_path)

    def test_custom_entries_appended(self, tmp_path: Path) -> None:
        overrides_dir = tmp_path / ".onex"
        overrides_dir.mkdir()
        overrides_file = overrides_dir / "antipattern-overrides.yaml"
        overrides_file.write_text(
            yaml.dump(
                {
                    "custom_entries": [
                        {
                            "name": "my_custom_rule",
                            "severity": "WARNING",
                            "enforcement": "advisory",
                            "category": "code_quality",
                            "pattern_type": "regex_line",
                            "pattern": r"TODO\(omn-",
                            "description": "Custom rule",
                            "rationale": "Custom rationale",
                            "discovered_date": "2026-01-01",
                            "source_ticket": "OMN-99999",
                        }
                    ]
                }
            )
        )
        result = resolve_antipatterns(tmp_path)
        names = {e.name for e in result.entries}
        assert "my_custom_rule" in names

    def test_no_overrides_file_returns_defaults(self, tmp_path: Path) -> None:
        result = resolve_antipatterns(tmp_path)
        defaults = load_default_registry()
        assert {e.name for e in result.entries} == {e.name for e in defaults.entries}

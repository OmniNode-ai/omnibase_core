# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the OMN-11912 canonical public API of antipattern_registry_loader.

Covers the acceptance criteria:
  - defaults only (no overrides file)
  - override disable (enabled=False removes an entry)
  - override severity
  - custom append
  - malformed override raises ValidationError
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.models.validation.model_antipattern_override_config import (
    ModelAntipatternOverrideConfig,
)
from omnibase_core.models.validation.model_antipattern_registry import (
    ModelAntipatternRegistry,
)
from omnibase_core.validation.antipattern_registry_loader import (
    load_default_antipatterns,
    load_repo_overrides,
    merge_antipatterns,
    resolve_antipatterns,
)


@pytest.mark.unit
class TestLoadDefaultAntipatterns:
    def test_returns_registry(self) -> None:
        result = load_default_antipatterns()
        assert isinstance(result, ModelAntipatternRegistry)

    def test_has_entries(self) -> None:
        result = load_default_antipatterns()
        assert len(result.entries) > 0

    def test_version_present(self) -> None:
        result = load_default_antipatterns()
        assert result.version != ""


@pytest.mark.unit
class TestLoadRepoOverrides:
    def test_no_file_returns_none(self, tmp_path: Path) -> None:
        result = load_repo_overrides(tmp_path)
        assert result is None

    def test_valid_override_file_returns_config(self, tmp_path: Path) -> None:
        onex_dir = tmp_path / ".onex"
        onex_dir.mkdir()
        (onex_dir / "antipattern-overrides.yaml").write_text(
            yaml.dump(
                {
                    "overrides": [
                        {"name": "hardcoded_ip", "severity": "WARNING"},
                    ]
                }
            )
        )
        result = load_repo_overrides(tmp_path)
        assert isinstance(result, ModelAntipatternOverrideConfig)
        assert len(result.overrides) == 1
        assert result.overrides[0].name == "hardcoded_ip"

    def test_malformed_override_raises_validation_error(self, tmp_path: Path) -> None:
        onex_dir = tmp_path / ".onex"
        onex_dir.mkdir()
        (onex_dir / "antipattern-overrides.yaml").write_text(
            yaml.dump(
                {
                    "overrides": [
                        {
                            "name": "hardcoded_ip",
                            "severity": "NOT_A_VALID_SEVERITY",
                        }
                    ]
                }
            )
        )
        with pytest.raises(ValidationError):
            load_repo_overrides(tmp_path)

    def test_unknown_extra_field_raises_validation_error(self, tmp_path: Path) -> None:
        onex_dir = tmp_path / ".onex"
        onex_dir.mkdir()
        (onex_dir / "antipattern-overrides.yaml").write_text(
            yaml.dump(
                {
                    "unknown_top_level_field": True,
                }
            )
        )
        with pytest.raises(ValidationError):
            load_repo_overrides(tmp_path)


@pytest.mark.unit
class TestMergeAntipatterns:
    def test_none_overrides_returns_defaults(self) -> None:
        defaults = load_default_antipatterns()
        result = merge_antipatterns(defaults, None)
        assert len(result.entries) == len(defaults.entries)

    def test_override_severity(self) -> None:
        defaults = load_default_antipatterns()
        config = ModelAntipatternOverrideConfig.model_validate(
            {
                "overrides": [{"name": "hardcoded_ip", "severity": "WARNING"}],
            }
        )
        result = merge_antipatterns(defaults, config)
        entry = next(e for e in result.entries if e.name == "hardcoded_ip")
        assert entry.severity == "WARNING"

    def test_override_enforcement(self) -> None:
        defaults = load_default_antipatterns()
        config = ModelAntipatternOverrideConfig.model_validate(
            {
                "overrides": [{"name": "obvious_comment", "enforcement": "blocking"}],
            }
        )
        result = merge_antipatterns(defaults, config)
        entry = next(e for e in result.entries if e.name == "obvious_comment")
        assert entry.enforcement == "blocking"

    def test_override_disable_removes_entry(self) -> None:
        defaults = load_default_antipatterns()
        names_before = {e.name for e in defaults.entries}
        assert "hardcoded_ip" in names_before

        config = ModelAntipatternOverrideConfig.model_validate(
            {
                "overrides": [{"name": "hardcoded_ip", "enabled": False}],
            }
        )
        result = merge_antipatterns(defaults, config)
        names_after = {e.name for e in result.entries}
        assert "hardcoded_ip" not in names_after
        assert len(result.entries) == len(defaults.entries) - 1

    def test_custom_entries_appended(self) -> None:
        defaults = load_default_antipatterns()
        config = ModelAntipatternOverrideConfig.model_validate(
            {
                "custom_entries": [
                    {
                        "name": "custom_test_rule",
                        "severity": "WARNING",
                        "enforcement": "advisory",
                        "category": "code_quality",
                        "pattern_type": "regex_line",
                        "pattern": r"CUSTOM_PATTERN",
                        "description": "Custom test rule",
                        "rationale": "Custom rationale for testing",
                        "discovered_date": "2026-01-01",
                        "source_ticket": "OMN-11912",
                    }
                ]
            }
        )
        result = merge_antipatterns(defaults, config)
        names = {e.name for e in result.entries}
        assert "custom_test_rule" in names
        assert len(result.entries) == len(defaults.entries) + 1

    def test_unknown_override_name_raises_value_error(self) -> None:
        defaults = load_default_antipatterns()
        config = ModelAntipatternOverrideConfig.model_validate(
            {
                "overrides": [{"name": "nonexistent_rule_xyz", "severity": "ERROR"}],
            }
        )
        with pytest.raises(ValueError, match="nonexistent_rule_xyz"):
            merge_antipatterns(defaults, config)


@pytest.mark.unit
class TestResolveAntipatterns:
    def test_defaults_only(self, tmp_path: Path) -> None:
        result = resolve_antipatterns(tmp_path)
        defaults = load_default_antipatterns()
        assert {e.name for e in result.entries} == {e.name for e in defaults.entries}

    def test_override_disable_via_file(self, tmp_path: Path) -> None:
        onex_dir = tmp_path / ".onex"
        onex_dir.mkdir()
        (onex_dir / "antipattern-overrides.yaml").write_text(
            yaml.dump({"overrides": [{"name": "hardcoded_ip", "enabled": False}]})
        )
        result = resolve_antipatterns(tmp_path)
        names = {e.name for e in result.entries}
        assert "hardcoded_ip" not in names

    def test_override_severity_via_file(self, tmp_path: Path) -> None:
        onex_dir = tmp_path / ".onex"
        onex_dir.mkdir()
        (onex_dir / "antipattern-overrides.yaml").write_text(
            yaml.dump({"overrides": [{"name": "hardcoded_ip", "severity": "WARNING"}]})
        )
        result = resolve_antipatterns(tmp_path)
        entry = next(e for e in result.entries if e.name == "hardcoded_ip")
        assert entry.severity == "WARNING"

    def test_custom_append_via_file(self, tmp_path: Path) -> None:
        onex_dir = tmp_path / ".onex"
        onex_dir.mkdir()
        (onex_dir / "antipattern-overrides.yaml").write_text(
            yaml.dump(
                {
                    "custom_entries": [
                        {
                            "name": "repo_specific_rule",
                            "severity": "ERROR",
                            "enforcement": "blocking",
                            "category": "architecture",
                            "pattern_type": "grep_code",
                            "pattern": "import_forbidden",
                            "description": "Repo-specific forbidden import",
                            "rationale": "This import is forbidden in this repo",
                            "discovered_date": "2026-01-01",
                            "source_ticket": "OMN-11912",
                        }
                    ]
                }
            )
        )
        result = resolve_antipatterns(tmp_path)
        names = {e.name for e in result.entries}
        assert "repo_specific_rule" in names

    def test_malformed_override_file_raises_validation_error(
        self, tmp_path: Path
    ) -> None:
        onex_dir = tmp_path / ".onex"
        onex_dir.mkdir()
        (onex_dir / "antipattern-overrides.yaml").write_text(
            yaml.dump(
                {"overrides": [{"name": "hardcoded_ip", "severity": "BAD_VALUE"}]}
            )
        )
        with pytest.raises(ValidationError):
            resolve_antipatterns(tmp_path)

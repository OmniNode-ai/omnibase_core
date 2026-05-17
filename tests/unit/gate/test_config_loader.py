# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.gate import discover_omnigate_config, load_omnigate_config
from omnibase_core.models.errors.model_onex_error import ModelOnexError

pytestmark = pytest.mark.unit


def _write_valid_config(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "version:",
                "  major: 1",
                "  minor: 0",
                "  patch: 0",
                "project_name: omnibase_core",
                "project_url: https://github.com/omninode-ai/omnibase_core",
                "checks:",
                "  - name: lint",
                "    run: uv run ruff check src/ tests/",
                "    timeout_seconds: 120",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


class TestDiscoverOmniGateConfig:
    def test_returns_first_existing_candidate(self, tmp_path: Path) -> None:
        first = tmp_path / "custom.yaml"
        second = tmp_path / ".omnigate.yaml"
        _write_valid_config(second)
        _write_valid_config(first)

        result = discover_omnigate_config(
            tmp_path,
            candidate_names=("custom.yaml", ".omnigate.yaml"),
        )

        assert result == first

    def test_returns_none_when_no_candidate_exists(self, tmp_path: Path) -> None:
        result = discover_omnigate_config(
            tmp_path,
            candidate_names=("custom.yaml",),
        )

        assert result is None

    def test_rejects_absolute_candidate_names(self, tmp_path: Path) -> None:
        with pytest.raises(ModelOnexError, match="relative file names"):
            discover_omnigate_config(
                tmp_path,
                candidate_names=("/tmp/.omnigate.yaml",),
            )

    def test_missing_root_raises_structured_error(self, tmp_path: Path) -> None:
        with pytest.raises(ModelOnexError, match="root does not exist"):
            discover_omnigate_config(tmp_path / "missing")


class TestLoadOmniGateConfig:
    def test_loads_yaml_into_typed_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".omnigate.yaml"
        _write_valid_config(config_path)

        config = load_omnigate_config(config_path)

        assert config.project_name == "omnibase_core"
        assert str(config.version) == "1.0.0"
        assert len(config.checks) == 1
        assert config.checks[0].name == "lint"
        assert config.checks[0].timeout_seconds == 120

    @pytest.mark.parametrize("content", ["", "   \n", "# comment only\n", "null\n"])
    def test_empty_yaml_fails_explicitly(self, tmp_path: Path, content: str) -> None:
        config_path = tmp_path / ".omnigate.yaml"
        config_path.write_text(content, encoding="utf-8")

        with pytest.raises(ModelOnexError, match="must not be empty"):
            load_omnigate_config(config_path)

    def test_non_mapping_yaml_fails_explicitly(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".omnigate.yaml"
        config_path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

        with pytest.raises(ModelOnexError, match="mapping at the document root"):
            load_omnigate_config(config_path)

    def test_pydantic_validation_error_propagates(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".omnigate.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "version:",
                    "  major: 1",
                    "  minor: 0",
                    "  patch: 0",
                    "project_name: omnibase_core",
                    "project_url: https://github.com/omninode-ai/omnibase_core",
                    "unexpected: true",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        with pytest.raises(ValidationError, match="unexpected"):
            load_omnigate_config(config_path)

    def test_missing_file_raises_structured_error(self, tmp_path: Path) -> None:
        with pytest.raises(ModelOnexError, match="file does not exist"):
            load_omnigate_config(tmp_path / ".omnigate.yaml")

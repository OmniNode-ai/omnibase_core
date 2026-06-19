# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the canonical Plugin* lifecycle class guard (OMN-13284)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from omnibase_core.validators.no_plugin_daemon_classes import main, validate_paths

if TYPE_CHECKING:
    import pytest


def test_flags_fake_plugin_daemon_class(tmp_path: Path) -> None:
    source = tmp_path / "plugin_bad.py"
    source.write_text(
        """
class DaemonBase:
    pass


class PluginXyzDaemon(DaemonBase):
    pass
""",
        encoding="utf-8",
    )

    findings = validate_paths([source])

    assert len(findings) == 1
    assert findings[0].class_name == "PluginXyzDaemon"
    assert findings[0].bases == ("DaemonBase",)
    assert findings[0].reason == "class name contains Daemon"


def test_allows_direct_plugin_compute_base_subclass(tmp_path: Path) -> None:
    source = tmp_path / "plugin_compute.py"
    source.write_text(
        """
from omnibase_infra.plugins import PluginComputeBase


class PluginDataService(PluginComputeBase):
    def execute(self, input_data, context):
        return input_data
""",
        encoding="utf-8",
    )

    assert validate_paths([source]) == []


def test_flags_compute_plugin_with_lifecycle_base(tmp_path: Path) -> None:
    source = tmp_path / "plugin_mixed_base.py"
    source.write_text(
        """
from omnibase_infra.plugins import PluginComputeBase


class ServiceBase:
    pass


class PluginDataNormalizer(PluginComputeBase, ServiceBase):
    def execute(self, input_data, context):
        return input_data
""",
        encoding="utf-8",
    )

    findings = validate_paths([source])

    assert len(findings) == 1
    assert findings[0].class_name == "PluginDataNormalizer"
    assert findings[0].bases == ("PluginComputeBase", "ServiceBase")
    assert findings[0].reason == "base class ServiceBase contains Service"


def test_allows_non_plugin_service_classes(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        """
class ServiceEnvelopeSigner:
    pass
""",
        encoding="utf-8",
    )

    assert validate_paths([source]) == []


def test_allows_plugin_compute_base_definition_itself(tmp_path: Path) -> None:
    source = tmp_path / "plugin_compute_base.py"
    source.write_text(
        """
class PluginComputeBase:
    def execute(self, input_data, context):
        raise NotImplementedError
""",
        encoding="utf-8",
    )

    assert validate_paths([source]) == []


def test_flags_consumer_lifecycle_plugin(tmp_path: Path) -> None:
    source = tmp_path / "plugin_consumer.py"
    source.write_text(
        """
class PluginKafkaConsumer:
    pass
""",
        encoding="utf-8",
    )

    findings = validate_paths([source])

    assert len(findings) == 1
    assert findings[0].class_name == "PluginKafkaConsumer"
    assert findings[0].reason == "class name contains Consumer"


def test_cli_returns_zero_for_clean_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "plugin_ok.py"
    source.write_text(
        """
from omnibase_infra.plugins import PluginComputeBase


class PluginJsonNormalizer(PluginComputeBase):
    def execute(self, input_data, context):
        return input_data
""",
        encoding="utf-8",
    )

    exit_code = main([str(tmp_path)])

    assert exit_code == 0


def test_cli_returns_nonzero_for_banned_class(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "plugin_worker.py"
    source.write_text(
        """
class WorkerBase:
    pass


class PluginBatchWorker(WorkerBase):
    pass
""",
        encoding="utf-8",
    )

    exit_code = main([str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "PluginBatchWorker" in captured.err

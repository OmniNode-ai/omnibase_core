# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-25070 AC7: ``onex --version`` reports the customer package a customer installed.

A customer installs ``omninode-onex`` (0.0.1 on 2026-11-18), which pins omnibase-core,
omnibase-infra and omnimarket. ``onex --version`` read only omnibase_core's metadata, so the
customer saw ``onex version 0.47.72``, a number of a package they never asked for. The
customer package's version wins when it is installed; a developer install without it keeps
reporting omnibase_core's version, never ``unknown``.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from importlib.metadata import PackageNotFoundError
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli, get_version

pytestmark = pytest.mark.unit


def _installed(versions: dict[str, str]) -> AbstractContextManager[Any]:
    def fake_version(distribution: str) -> str:
        if distribution in versions:
            return versions[distribution]
        raise PackageNotFoundError(distribution)

    return patch("importlib.metadata.version", side_effect=fake_version)


def test_customer_install_reports_the_customer_package_version() -> None:
    with _installed({"omninode-onex": "0.0.1", "omnibase_core": "0.47.72"}):
        assert get_version() == "0.0.1"


def test_developer_install_without_the_customer_package_reports_core() -> None:
    with _installed({"omnibase_core": "0.47.72"}):
        assert get_version() == "0.47.72"


def test_onex_info_keeps_labelling_the_core_version_as_core() -> None:
    # Independent review of #2343: `onex info` labels its line "omnibase_core version",
    # so on a customer install it must still print omnibase_core's own version there.
    with _installed({"omninode-onex": "0.0.1", "omnibase_core": "0.47.72"}):
        result = CliRunner().invoke(cli, ["info"])
    assert result.exit_code == 0, result.output
    assert "omnibase_core version: 0.47.72" in result.output


def test_onex_version_flag_prints_the_customer_package_version() -> None:
    with _installed({"omninode-onex": "0.0.1", "omnibase_core": "0.47.72"}):
        result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "onex version 0.0.1"

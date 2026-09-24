# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19443: onex doctor runs on a clean install instead of crashing.

AC1: with KAFKA_BOOTSTRAP_SERVERS unset the kafka check reports not
configured and doctor prints its summary.
AC2: every shipped doctor check survives an empty environment.
"""

from __future__ import annotations

import pytest

from omnibase_core.cli.cli_doctor import _BUILTIN_CHECKS
from omnibase_core.doctor.checks.check_kafka import CheckKafka
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue

pytestmark = pytest.mark.unit


def test_check_kafka_reports_not_configured_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC1 falsifier: an unset KAFKA_BOOTSTRAP_SERVERS must not raise."""
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)
    result = CheckKafka().run()
    assert result.status == EnumHealthStatusValue.UNKNOWN
    assert "KAFKA_BOOTSTRAP_SERVERS" in result.message


@pytest.mark.parametrize("check_cls", _BUILTIN_CHECKS, ids=lambda c: c.check_id)
def test_every_builtin_check_survives_empty_environment(
    check_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2 falsifier: a parametrised pytest over the registered doctor checks
    with an empty environment must not raise for any of them."""
    for var in (
        "KAFKA_BOOTSTRAP_SERVERS",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "LINEAR_API_KEY",
        "OMNI_HOME",
        "OMNI_WORKTREES",
    ):
        monkeypatch.delenv(var, raising=False)
    check = check_cls()
    result = check.run()
    assert result.status is not None

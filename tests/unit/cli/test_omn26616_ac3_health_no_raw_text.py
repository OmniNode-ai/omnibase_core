# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-26616 AC3: every failure branch of onex health prints plain words and a Fix line.

Each case forces one branch to fail with a distinctive raw text and asserts the
text never reaches the screen or the JSON, and that a Fix line is present.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import NoReturn

import pytest
from click.testing import CliRunner

from omnibase_core.cli import cli_commands
from omnibase_core.cli.cli_commands import cli

_RAW = "RAWSECRET /private/path/leak.py"


def _boom(*_args: object, **_kwargs: object) -> NoReturn:
    raise RuntimeError(_RAW)


def _force_core_imports(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setitem(sys.modules, "omnibase_core.enums.enum_core_error_code", None)
    return "core"


def _force_validation_import(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setitem(sys.modules, "omnibase_core.validation.validator_cli", None)
    return "validation"


def _force_validation_fault(monkeypatch: pytest.MonkeyPatch) -> str:
    import omnibase_core.validation.validator_cli as module

    def suite(*_a: object, **_k: object) -> NoReturn:
        raise ValueError(_RAW)

    monkeypatch.setattr(module, "ServiceValidationSuite", suite)
    return "validation"


def _force_error_handling(monkeypatch: pytest.MonkeyPatch) -> str:
    import omnibase_core.errors.model_onex_error as module

    def error(*_a: object, **_k: object) -> NoReturn:
        raise TypeError(_RAW)

    monkeypatch.setattr(module, "ModelOnexError", error)
    return "error"


def _force_generic(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(cli_commands, "_check_kafka_reachable", _boom)
    return "kafka"


def _force_bad_port(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "host:notaport")
    return "kafka"


_BRANCHES = [
    _force_core_imports,
    _force_validation_import,
    _force_validation_fault,
    _force_error_handling,
    _force_generic,
    _force_bad_port,
]


@pytest.mark.parametrize("force", _BRANCHES, ids=lambda f: f.__name__)
def test_failure_branch_prints_plain_words_and_a_fix(
    force: Callable[[pytest.MonkeyPatch], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    component = force(monkeypatch)
    for flags in ([], ["--json"]):
        result = CliRunner().invoke(cli, ["health", "--component", component, *flags])
        output = result.output
        assert result.exit_code != 0, output
        assert "RAWSECRET" not in output
        assert "leak.py" not in output
        assert "halted" not in output
        assert "sys.modules" not in output
        assert "Import error" not in output
        assert "Error: " not in output
        assert "notaport" not in output
        assert "Fix:" in output
        if "--json" in flags:
            assert json.loads(output)["checks"][0]["healthy"] is False

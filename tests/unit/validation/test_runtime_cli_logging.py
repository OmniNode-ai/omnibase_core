# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI logging must not retain streams or close an embedding caller's handlers."""

from __future__ import annotations

import io
import logging
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.models.logging.model_cli_logging import cli_logging
from omnibase_core.nodes.node_enum_member_casing_check_compute.runtime_enum_member_casing_check import (
    main as enum_main,
)
from omnibase_core.nodes.node_literal_duplication_check_compute.runtime_literal_duplication_check import (
    main as literal_main,
)
from omnibase_core.nodes.node_naming_convention_check_compute.runtime_naming_convention_check import (
    main as naming_main,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("main", "flags"),
    [(enum_main, ["--directory"]), (literal_main, []), (naming_main, [])],
    ids=["enum", "literal", "naming"],
)
@pytest.mark.parametrize("missing", [False, True], ids=["clean", "missing"])
def test_cli_preserves_caller_logging(
    main: Callable[[list[str]], int],
    flags: list[str],
    missing: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    root = logging.getLogger()
    stream = io.StringIO()
    caller_handler = logging.StreamHandler(stream)
    root.addHandler(caller_handler)
    previous_handlers = root.handlers[:]
    previous_level = root.level
    target = tmp_path / "missing" if missing else tmp_path
    try:
        with patch.object(caller_handler, "close") as close:
            assert main([*flags, str(target)]) == int(missing)
            assert root.handlers == previous_handlers
            assert root.level == previous_level
            close.assert_not_called()
        # The CLI uses its own current stderr and never writes to the caller's stream.
        assert capsys.readouterr().err
        assert stream.getvalue() == ""
        root.log(logging.CRITICAL, "caller still receives logs")
        assert stream.getvalue() == "caller still receives logs\n"
    finally:
        root.handlers[:] = previous_handlers
        root.removeHandler(caller_handler)
        root.setLevel(previous_level)
        caller_handler.close()


def test_cli_logging_restores_caller_after_exception() -> None:
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    with (
        pytest.raises(RuntimeError, match="validation interrupted"),
        cli_logging(logging.DEBUG),
    ):
        raise RuntimeError("validation interrupted")
    assert root.handlers == previous_handlers
    assert root.level == previous_level

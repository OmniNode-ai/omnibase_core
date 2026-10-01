# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Prove validators aggregate pre-commit's whole filename batch (OMN-20241)."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import pytest

from omnibase_core.nodes.node_no_io_outside_effects_check_compute.runtime_no_io_outside_effects_check import (
    main as no_io_main,
)
from omnibase_core.validation.validator_transport_import import main as transport_main

type Validator = Literal["transport", "no-io"]

_TRANSPORT_MODULE = "omnibase_core.validation.validator_transport_import"
_NO_IO_MODULE = (
    "omnibase_core.nodes.node_no_io_outside_effects_check_compute."
    "runtime_no_io_outside_effects_check"
)
_CLEAN_HANDLER = "def run(intents):\n    return intents\n"
_COMPUTE_CONTRACT = (
    "name: node_x\nnode_type: compute\ndescriptor:\n  node_archetype: compute\n"
)
_GIT_HANDLER = (
    "import git\n\n\ndef clone(url):\n    return git.Repo.clone_from(url, '.')\n"
)


@pytest.fixture(params=["transport", "no-io"])
def validator(request: pytest.FixtureRequest) -> Validator:
    """Exercise both real validators through the same batch assertions."""
    value = request.param
    assert value in ("transport", "no-io")
    return "transport" if value == "transport" else "no-io"


def _make_batch(tmp_path: Path, validator: Validator, *, planted: bool) -> list[Path]:
    """Build 12 files; no-I/O files each get a sibling compute contract."""
    paths = []
    for index in range(12):
        if validator == "no-io":
            node_dir = tmp_path / f"node_{index}_compute"
            node_dir.mkdir()
            (node_dir / "contract.yaml").write_text(_COMPUTE_CONTRACT, encoding="utf-8")
            path = node_dir / "handler.py"
        else:
            path = tmp_path / f"node_{index}.py"
        source = _CLEAN_HANDLER
        if planted and index == 7:
            source = "import httpx\n" if validator == "transport" else _GIT_HANDLER
        path.write_text(source, encoding="utf-8")
        paths.append(path)
    return paths


def _main(validator: Validator) -> Callable[[list[str] | None], int]:
    return transport_main if validator == "transport" else no_io_main


@pytest.mark.unit
def test_clean_batch_returns_zero(tmp_path: Path, validator: Validator) -> None:
    paths = _make_batch(tmp_path, validator, planted=False)
    assert _main(validator)([str(path) for path in paths]) == 0


@pytest.mark.unit
def test_planted_batch_matches_single_file_verdict(
    tmp_path: Path, validator: Validator, capsys: pytest.CaptureFixture[str]
) -> None:
    paths = _make_batch(tmp_path, validator, planted=True)
    batch_verdict = _main(validator)([str(path) for path in paths])
    assert batch_verdict == 1
    assert str(paths[7]) in capsys.readouterr().out

    single_verdict = _main(validator)([str(paths[7])])
    assert single_verdict == batch_verdict
    assert str(paths[7]) in capsys.readouterr().out


@pytest.mark.unit
@pytest.mark.timeout(120)
@pytest.mark.parametrize("planted", [False, True], ids=["clean", "planted"])
def test_module_entrypoint_aggregates_batch(
    tmp_path: Path, validator: Validator, planted: bool
) -> None:
    paths = _make_batch(tmp_path, validator, planted=planted)
    module = _TRANSPORT_MODULE if validator == "transport" else _NO_IO_MODULE
    result = subprocess.run(
        [sys.executable, "-m", module, *[str(path) for path in paths]],
        # Resolve modules from this checkout even when using a shared virtualenv.
        cwd=Path(__file__).resolve().parents[3] / "src",
        capture_output=True,
        text=True,
        check=False,
        # Cold omnibase_core imports can exceed 30s on a busy developer host.
        timeout=90,
    )
    assert result.returncode == (1 if planted else 0), result.stdout + result.stderr
    if planted:
        assert str(paths[7]) in result.stdout

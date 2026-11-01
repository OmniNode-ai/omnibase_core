# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-21875: a writer-app pin bump may refresh the uv.lock digest in YAML files.

omnimarket's work contracts record ``sha256`` of ``uv.lock``. When the OCC
writer app bumps a sibling pin, ``uv.lock`` changes, so every work contract's
digest line changes with it (omnimarket#4654: pyproject.toml, uv.lock and 70
contracts). The pin-swap classifier refused those YAML paths, so the bump fell
through to the evidence gate and failed on the already merged ticket contract.

The exemption is derived, never asserted: every changed line of such a file
must swap a 64-hex value whose old value is sha256 of the merge base's
``uv.lock`` and whose new value is sha256 of the head's.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tests.ci.test_receipt_gate_writer_pin_only_in_job_omn17427 import (
    _assert_output,
    _run,
)
from tests.ci.test_receipt_gate_writer_pin_swap_omn20068 import PROJECT, _prepare

pytestmark = pytest.mark.unit

LOCK_BASE = 'version = 1\n[[package]]\nname = "omnibase-core"\nversion = "0.1.0"\n'
LOCK_HEAD = LOCK_BASE.replace('"0.1.0"', '"0.1.1"')
BASE_DIGEST = hashlib.sha256(LOCK_BASE.encode()).hexdigest()
HEAD_DIGEST = hashlib.sha256(LOCK_HEAD.encode()).hexdigest()
C1 = "src/x/configs/work_contracts/contracts/F01-01.yaml"
C2 = "src/x/configs/work_contracts/contracts/F01-02.yaml"


def _contract(digest: str, expected_exit: int = 0) -> str:
    return (
        "acceptance:\n"
        "  kind: command\n"
        "  spec:\n"
        "    environment:\n"
        "      path: uv.lock\n"
        f"      sha256: {digest}\n"
        f"    expected_exit: {expected_exit}\n"
    )


BASE = {
    "pyproject.toml": PROJECT,
    "uv.lock": LOCK_BASE,
    C1: _contract(BASE_DIGEST),
    C2: _contract(BASE_DIGEST),
}
HEAD = {
    "pyproject.toml": PROJECT.replace("0.1.0", "0.1.1"),
    "uv.lock": LOCK_HEAD,
    C1: _contract(HEAD_DIGEST),
    C2: _contract(HEAD_DIGEST),
}


def test_lock_digest_refresh_is_exempt(tmp_path: Path) -> None:
    env = _prepare(tmp_path, HEAD, base_changes=BASE)
    result = _run(env)
    _assert_output(env, exempt=True)
    assert "pin-swap-only change" in result.stdout
    assert "uv.lock digest refreshed in 2 file(s)" in result.stdout


def test_lock_digest_refresh_without_manifest_is_exempt(tmp_path: Path) -> None:
    env = _prepare(
        tmp_path,
        {"uv.lock": LOCK_HEAD, C1: _contract(HEAD_DIGEST)},
        base_changes=BASE,
    )
    result = _run(env)
    _assert_output(env, exempt=True)
    assert "uv.lock digest refreshed in 1 file(s)" in result.stdout


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        pytest.param(
            {C1: _contract("f" * 64)},
            f"{C1} line 6 is not solely a uv.lock digest refresh",
            id="refuses-new-digest-not-head-lock",
        ),
        pytest.param(
            {"uv.lock": LOCK_BASE},
            "requires exactly one changed uv.lock",
            id="refuses-digest-swap-without-lock-change",
        ),
        pytest.param(
            {C1: _contract(HEAD_DIGEST, expected_exit=1)},
            f"{C1} line 7 is not solely a uv.lock digest refresh",
            id="refuses-other-changed-line",
        ),
        pytest.param(
            {C1: _contract(HEAD_DIGEST) + "extra: true\n"},
            f"{C1} adds or removes a line",
            id="refuses-added-line",
        ),
        pytest.param(
            {"src/x/new.yaml": _contract(HEAD_DIGEST)},
            "file is added or deleted: src/x/new.yaml",
            id="refuses-added-yaml",
        ),
        pytest.param(
            {"src/x/run.py": "x = 1\n"},
            "path is not allowed for a pin swap: src/x/run.py",
            id="refuses-source-file",
        ),
    ],
)
def test_lock_digest_refresh_refuses(
    tmp_path: Path, changes: dict[str, str], reason: str
) -> None:
    env = _prepare(tmp_path, {**HEAD, **changes}, base_changes=BASE)
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "OCC writer app is not exempt:" in result.stdout
    assert reason in result.stdout


def test_refuses_digest_swap_whose_old_value_is_not_base_lock(tmp_path: Path) -> None:
    env = _prepare(
        tmp_path,
        HEAD,
        base_changes={**BASE, C2: _contract("e" * 64)},
    )
    result = _run(env)
    _assert_output(env, exempt=False)
    assert f"{C2} line 6 is not solely a uv.lock digest refresh" in result.stdout

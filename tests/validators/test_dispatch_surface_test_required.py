# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the dispatch-surface real-dispatch-test gate (OMN-12960)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators.dispatch_surface_test_required import (
    is_dispatch_surface,
    is_real_dispatch_test,
    main,
)

_REAL_DISPATCH_TEST_BODY = (
    "from omnibase_infra.runtime.message_dispatch_engine import "
    "MessageDispatchEngine\n\n"
    "def test_live():\n"
    "    eng = MessageDispatchEngine\n"
)
_ISOLATION_TEST_BODY = "def test_handler():\n    handler.handle({})\n"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("src/omnibase_infra/runtime/auto_wiring/handler_wiring.py", True),
        ("repo/src/omnibase_infra/runtime/message_dispatch_engine.py", True),
        ("src/omnibase_core/utils/util_envelope_unwrap.py", True),
        ("src/omnimarket/nodes/evidence_pipeline_native.py", True),
        ("src/omnibase_core/utils/util_canonical_hash.py", False),  # not a surface
        ("tests/test_handler_wiring.py", False),  # a test, not a source surface
        ("docs/handler_wiring.md", False),  # not python/src
    ],
)
def test_is_dispatch_surface(path: str, expected: bool) -> None:
    assert is_dispatch_surface(path) is expected


def test_is_real_dispatch_test_recognises_real_driver() -> None:
    assert is_real_dispatch_test("tests/test_x.py", _REAL_DISPATCH_TEST_BODY)


def test_is_real_dispatch_test_rejects_isolation_test() -> None:
    assert not is_real_dispatch_test("tests/test_x.py", _ISOLATION_TEST_BODY)


def test_is_real_dispatch_test_rejects_non_test_file() -> None:
    assert not is_real_dispatch_test("src/x.py", _REAL_DISPATCH_TEST_BODY)


def test_main_passes_when_no_surface_touched(tmp_path: Path) -> None:
    f = tmp_path / "src" / "omnibase_core" / "utils" / "util_canonical_hash.py"
    f.parent.mkdir(parents=True)
    f.write_text("x = 1\n")
    assert main([str(f)]) == 0


def test_main_fails_on_surface_without_real_dispatch_test(tmp_path: Path) -> None:
    surface = tmp_path / "src" / "pkg" / "auto_wiring" / "handler_wiring.py"
    surface.parent.mkdir(parents=True)
    surface.write_text("x = 1\n")
    iso = tmp_path / "tests" / "test_iso.py"
    iso.parent.mkdir(parents=True)
    iso.write_text(_ISOLATION_TEST_BODY)
    assert main([str(surface), str(iso)]) == 1


def test_main_passes_on_surface_with_real_dispatch_test(tmp_path: Path) -> None:
    surface = tmp_path / "src" / "pkg" / "auto_wiring" / "handler_wiring.py"
    surface.parent.mkdir(parents=True)
    surface.write_text("x = 1\n")
    real = tmp_path / "tests" / "test_real.py"
    real.parent.mkdir(parents=True)
    real.write_text(_REAL_DISPATCH_TEST_BODY)
    assert main([str(surface), str(real)]) == 0


def test_main_respects_suppression_token(tmp_path: Path) -> None:
    surface = tmp_path / "src" / "pkg" / "auto_wiring" / "handler_wiring.py"
    surface.parent.mkdir(parents=True)
    surface.write_text("x = 1  # dispatch-surface-test-ok: comment-only edit\n")
    assert main([str(surface)]) == 0

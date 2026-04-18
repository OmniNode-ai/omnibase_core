# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for scripts/emit_ts_types.py.

Verifies:
1. ``main()`` writes a file at the requested path and returns 0 on success.
2. Output is valid JSON with the expected top-level shape.
3. ``$defs`` contains a key for every model in the ``MODELS`` dict.
4. Each entry is a Pydantic-generated object schema.
5. ``main()`` returns a non-zero exit code when argv is malformed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

from emit_ts_types import MODELS, main  # type: ignore[import-not-found]


@pytest.fixture(autouse=True)
def _restore_argv() -> Any:
    saved = list(sys.argv)
    try:
        yield
    finally:
        sys.argv = saved


def test_main_writes_combined_schema(tmp_path: Path) -> None:
    target = tmp_path / "onex-models.json"
    sys.argv = ["emit_ts_types.py", str(target)]

    rc = main()

    assert rc == 0
    assert target.exists(), "output file was not written"

    payload = json.loads(target.read_text())

    assert payload["$id"] == "https://omninode.ai/schemas/omnidash-v2.json"
    assert "$defs" in payload
    defs = payload["$defs"]
    assert isinstance(defs, dict)

    for name in MODELS:
        assert name in defs, f"missing $defs entry for {name}"
        entry = defs[name]
        assert isinstance(entry, dict), f"{name} entry is not a dict"
        # Pydantic-generated object schemas declare "type": "object" at the top
        # level (or route through "$ref" / "allOf"/"anyOf" for composed models).
        has_object_shape = (
            entry.get("type") == "object"
            or "$ref" in entry
            or "allOf" in entry
            or "anyOf" in entry
            or "oneOf" in entry
        )
        assert has_object_shape, (
            f"{name} schema does not look like an object schema: {entry!r}"
        )


def test_main_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir" / "onex-models.json"
    sys.argv = ["emit_ts_types.py", str(target)]

    rc = main()

    assert rc == 0
    assert target.exists()


def test_main_usage_error_on_missing_argument(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sys.argv = ["emit_ts_types.py"]

    rc = main()

    assert rc == 1
    err = capsys.readouterr().err
    assert "usage:" in err


def test_main_usage_error_on_extra_arguments(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    sys.argv = ["emit_ts_types.py", str(tmp_path / "a.json"), "extra"]

    rc = main()

    assert rc == 1
    err = capsys.readouterr().err
    assert "usage:" in err

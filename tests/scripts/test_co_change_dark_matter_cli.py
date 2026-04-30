# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the co-change dark matter CLI script (Task 13, OMN-10365)."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "analysis"
    / "co_change_dark_matter.py"
)


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
    )


class TestJsonFlag:
    def test_json_flag_exits_0(self, tmp_path: Path) -> None:
        result = _run("--json", cwd=tmp_path)
        assert result.returncode == 0, result.stderr

    def test_json_output_is_valid_json(self, tmp_path: Path) -> None:
        result = _run("--json", cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert "pairs" in payload

    def test_json_schema_matches_pairs(self, tmp_path: Path) -> None:
        result = _run("--json", cwd=tmp_path)
        payload = json.loads(result.stdout)
        for pair in payload["pairs"]:
            assert {"a", "b", "npmi", "co_changes"} <= set(pair.keys()), pair
            assert isinstance(pair["npmi"], float), pair
            assert isinstance(pair["co_changes"], int), pair
            assert isinstance(pair["a"], str), pair
            assert isinstance(pair["b"], str), pair

    def test_json_exits_0_on_empty_result(self, tmp_path: Path) -> None:
        # tmp_path is a git-less directory with no git log → empty result
        result = _run("--json", cwd=tmp_path)
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload == {"pairs": []}


class TestWriteStateFlag:
    def test_write_state_creates_file(self, tmp_path: Path) -> None:
        result = _run("--write-state", cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        state_file = tmp_path / ".onex_state" / "co-change-map.json"
        assert state_file.exists(), f"Expected {state_file} to exist"

    def test_write_state_content_is_valid_json(self, tmp_path: Path) -> None:
        _run("--write-state", cwd=tmp_path)
        state_file = tmp_path / ".onex_state" / "co-change-map.json"
        payload = json.loads(state_file.read_text())
        assert "pairs" in payload

    def test_write_state_overwrites_existing(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".onex_state"
        state_dir.mkdir(parents=True)
        state_file = state_dir / "co-change-map.json"
        state_file.write_text('{"old": true}')
        result = _run("--write-state", cwd=tmp_path)
        assert result.returncode == 0
        payload = json.loads(state_file.read_text())
        assert "pairs" in payload
        assert "old" not in payload

    def test_write_state_mkdir_p(self, tmp_path: Path) -> None:
        # Ensure .onex_state does not exist before the call
        state_dir = tmp_path / ".onex_state"
        assert not state_dir.exists()
        result = _run("--write-state", cwd=tmp_path)
        assert result.returncode == 0
        assert state_dir.exists()


class TestNoArgsHumanReadable:
    def test_no_args_exits_0(self, tmp_path: Path) -> None:
        result = _run(cwd=tmp_path)
        assert result.returncode == 0, result.stderr

    def test_no_args_output_is_not_json(self, tmp_path: Path) -> None:
        result = _run(cwd=tmp_path)
        # Human-readable output should not be parseable as a JSON object
        # (it's tabular text). On empty result it may just print a header line.
        try:
            parsed = json.loads(result.stdout)
            # If it parses, it must not be the API JSON schema (a dict with "pairs")
            assert "pairs" not in parsed
        except json.JSONDecodeError:
            pass  # expected for human-readable output

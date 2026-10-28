# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the check-action-pins CLI (OMN-17427).

The CLI reads the overlay and the workflow files, runs the pure handler, and
exits 0 on PASS/WARN and 1 on FAIL/ERROR. Fixture text is assembled from
``_ORG`` so this file holds no literal first-party reference.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers.handler_action_pin_cli import (
    DEFAULT_OVERLAY,
    main,
    overlay_exception_growth,
)
from omnibase_core.models.action_pins import ModelActionPinOverlay
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

_ORG = "OmniNode-ai"
_SHA = "a1b2" * 10
_TAG = "dev-20261018024445-b6ee996befa1"
_FIRST = f"{_ORG}/omnibase_core/.github/workflows/zone-filter.yml"
_EXC_USES = f"{_ORG}/omniclaude/.github/workflows/kb-gate.yml@{_SHA}"


def _overlay_doc(*exceptions: str) -> dict[str, object]:
    return {
        "first_party_orgs": [_ORG],
        "tag_pattern": r"dev-\d{14}-[0-9a-f]{12}",
        "first_party_main": "warn",
        "known_exceptions": [
            {"uses": uses, "reason": "no dev-merge tag exists for this commit"}
            for uses in exceptions
        ],
    }


def _repo(tmp_path: Path, *uses: str, overlay: dict[str, object] | None = None) -> Path:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    body = "jobs:\n  a:\n    steps:\n" + "".join(f"      - uses: {u}\n" for u in uses)
    (workflows / "ci.yml").write_text(body, encoding="utf-8")
    (tmp_path / DEFAULT_OVERLAY).write_text(
        yaml.safe_dump(overlay if overlay is not None else _overlay_doc()),
        encoding="utf-8",
    )
    return tmp_path


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
        env=scrub_git_location_env(),
    )


class TestFullTree:
    def test_pinned_and_tagged_pass(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"actions/checkout@{_SHA}", f"{_FIRST}@{_TAG}")
        assert main(["--root", str(root)]) == 0

    def test_third_party_tag_fails(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, "actions/checkout@v4")
        assert main(["--root", str(root)]) == 1

    def test_first_party_sha_fails(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"{_FIRST}@{_SHA}")
        assert main(["--root", str(root)]) == 1

    def test_known_exception_and_main_warn_but_pass(self, tmp_path: Path) -> None:
        root = _repo(
            tmp_path,
            _EXC_USES,
            f"{_FIRST}@main",
            overlay=_overlay_doc(_EXC_USES),
        )
        assert main(["--root", str(root)]) == 0

    def test_unused_exception_warns_but_passes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        root = _repo(tmp_path, f"{_FIRST}@{_TAG}", overlay=_overlay_doc(_EXC_USES))
        assert main(["--root", str(root)]) == 0
        assert "no longer used" in capsys.readouterr().out

    def test_zero_uses_is_error_not_pass(self, tmp_path: Path) -> None:
        root = _repo(tmp_path)
        assert main(["--root", str(root)]) == 1

    def test_no_workflows_dir_is_error(self, tmp_path: Path) -> None:
        (tmp_path / DEFAULT_OVERLAY).write_text(
            yaml.safe_dump(_overlay_doc()), encoding="utf-8"
        )
        assert main(["--root", str(tmp_path)]) == 1


class TestOverlayLoading:
    def test_missing_overlay_is_error(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"actions/checkout@{_SHA}")
        (root / DEFAULT_OVERLAY).unlink()
        assert main(["--root", str(root)]) == 1

    def test_invalid_overlay_is_error(self, tmp_path: Path) -> None:
        root = _repo(
            tmp_path,
            f"actions/checkout@{_SHA}",
            overlay={"first_party_orgs": [], "tag_pattern": "x"},
        )
        assert main(["--root", str(root)]) == 1

    def test_overlay_path_is_an_option(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"{_FIRST}@{_TAG}")
        (root / DEFAULT_OVERLAY).rename(root / "other.yaml")
        assert main(["--root", str(root), "--overlay", "other.yaml"]) == 0


class TestStagedFiles:
    def test_staged_workflow_is_judged(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, "actions/checkout@v4")
        assert main(["--root", str(root), ".github/workflows/ci.yml"]) == 1

    def test_staged_non_workflow_is_a_no_op(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, "actions/checkout@v4")
        assert main(["--root", str(root), "README.md"]) == 0

    def test_staged_run_skips_the_unused_exception_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        root = _repo(tmp_path, f"{_FIRST}@{_TAG}", overlay=_overlay_doc(_EXC_USES))
        assert main(["--root", str(root), ".github/workflows/ci.yml"]) == 0
        assert "no longer used" not in capsys.readouterr().out


class TestRatchet:
    def _committed(self, tmp_path: Path, base: dict[str, object]) -> Path:
        root = _repo(tmp_path, f"{_FIRST}@{_TAG}", overlay=base)
        _git(root, "init", "-q", "-b", "main")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "base")
        return root

    def test_new_exception_is_refused(self, tmp_path: Path) -> None:
        root = self._committed(tmp_path, _overlay_doc())
        (root / DEFAULT_OVERLAY).write_text(
            yaml.safe_dump(_overlay_doc(_EXC_USES)), encoding="utf-8"
        )
        assert main(["--root", str(root), "--ratchet-base-ref", "HEAD"]) == 1

    def test_unchanged_or_shrunk_overlay_passes(self, tmp_path: Path) -> None:
        root = self._committed(tmp_path, _overlay_doc(_EXC_USES))
        assert main(["--root", str(root), "--ratchet-base-ref", "HEAD"]) == 0

    def test_missing_base_ref_is_error(self, tmp_path: Path) -> None:
        root = self._committed(tmp_path, _overlay_doc())
        assert main(["--root", str(root), "--ratchet-base-ref", "no-such-ref"]) == 1

    def test_overlay_absent_at_base_is_the_introduction(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"{_FIRST}@{_TAG}", overlay=_overlay_doc(_EXC_USES))
        (root / DEFAULT_OVERLAY).rename(root / "moved.yaml")
        _git(root, "init", "-q", "-b", "main")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "base")
        (root / "moved.yaml").rename(root / DEFAULT_OVERLAY)
        assert main(["--root", str(root), "--ratchet-base-ref", "HEAD"]) == 0

    def test_growth_names_the_added_entry(self) -> None:
        base = ModelActionPinOverlay.model_validate(_overlay_doc())
        current = ModelActionPinOverlay.model_validate(_overlay_doc(_EXC_USES))
        assert overlay_exception_growth(current, None) == []
        assert overlay_exception_growth(current, base) == [
            f"overlay grew: known exception {_EXC_USES} is not in the base overlay"
        ]
        assert overlay_exception_growth(base, current) == []


class TestReport:
    def test_report_json_is_written(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, "actions/checkout@v4")
        out = tmp_path / "report.json"
        assert main(["--root", str(root), "--report-json", str(out)]) == 1
        report = json.loads(out.read_text(encoding="utf-8"))
        assert report["overall_status"] == "FAIL"
        assert report["findings"][0]["validator_id"] == "action-pins"

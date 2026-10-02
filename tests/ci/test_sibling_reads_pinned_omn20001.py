# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20001: a workflow reads a sibling repo only at a pinned revision.

Ruling 2026-10-01: each repo checks only itself; any read of a sibling repo
uses the revision this repo has pinned, never the sibling's live branch, so a
merge in one repo cannot turn another repo red. This gate parses every
``.github/workflows`` file and fails on a cross-repo ``uses:`` or a sibling
``actions/checkout`` whose ``ref`` is absent or a branch name.

An expression ref (``${{ ... }}``) is accepted: it is resolved from a recorded
sha at run time (the receipt-gate / occ-preflight OCC evidence sha, the
``core-ref`` input), not a moving branch.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent.parent / ".github" / "workflows"
_ORG = "OmniNode-ai/"
_SELF = "omnibase_core"
_SHA = re.compile(r"^[0-9a-f]{40}$")
# Matrix-target checkouts are the WRITE side of the producer-notifies-consumer
# flow (they push a pin-bump PR to the downstream repo), not a read for a check.
_WRITE_TARGET = "${{ matrix.repo }}"


def _sibling_reads(workflows_dir: Path) -> list[tuple[str, str, str | None]]:
    """Return (workflow, what, ref) for every sibling read in the workflows."""
    reads: list[tuple[str, str, str | None]] = []
    for path in sorted(workflows_dir.glob("*.y*ml")):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        jobs = loaded.get("jobs") if isinstance(loaded, dict) else None
        if not isinstance(jobs, dict):
            continue
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            uses_list = [job.get("uses")]
            steps = job.get("steps") if isinstance(job.get("steps"), list) else []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses")
                with_ = step.get("with") or {}
                repo = with_.get("repository") if isinstance(with_, dict) else None
                if (
                    isinstance(uses, str)
                    and uses.startswith("actions/checkout@")
                    and isinstance(repo, str)
                    and repo.startswith(_ORG)
                    and repo[len(_ORG) :] not in (_SELF, _WRITE_TARGET)
                ):
                    ref = with_.get("ref")
                    reads.append((path.name, f"checkout {repo}", ref))
                uses_list.append(uses)
            for uses in uses_list:
                if not isinstance(uses, str) or not uses.startswith(_ORG):
                    continue
                spec, _, ref = uses.rpartition("@")
                if spec[len(_ORG) :].partition("/")[0] != _SELF:
                    reads.append((path.name, f"uses {spec}", ref))
    return reads


def _is_pinned(ref: str | None) -> bool:
    if ref is None:
        return False
    ref = str(ref)
    return bool(_SHA.match(ref)) or ref.startswith("${{")


@pytest.mark.unit
def test_every_sibling_read_is_pinned() -> None:
    reads = _sibling_reads(WORKFLOWS_DIR)
    assert reads, "positive control: the workflows contain sibling reads"
    unpinned = [r for r in reads if not _is_pinned(r[2])]
    assert not unpinned, f"sibling reads at a live branch or no ref: {unpinned}"


@pytest.mark.unit
def test_falsifier_detects_branch_and_missing_ref(tmp_path: Path) -> None:
    (tmp_path / "bad.yml").write_text(
        """\
name: bad
on: push
jobs:
  a:
    uses: OmniNode-ai/omniclaude/.github/workflows/x.yml@main
  b:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          repository: OmniNode-ai/omnibase_compat
          ref: dev
      - uses: actions/checkout@v7
        with:
          repository: OmniNode-ai/onex_change_control
      - uses: actions/checkout@v7
        with:
          repository: OmniNode-ai/omnibase_spi
          ref: b6117e4efb1b734e974a8695f175cdac1f964db9
""",
        encoding="utf-8",
    )
    reads = _sibling_reads(tmp_path)
    assert [r[0:2] for r in reads if not _is_pinned(r[2])] == [
        ("bad.yml", "uses OmniNode-ai/omniclaude/.github/workflows/x.yml"),
        ("bad.yml", "checkout OmniNode-ai/omnibase_compat"),
        ("bad.yml", "checkout OmniNode-ai/onex_change_control"),
    ]

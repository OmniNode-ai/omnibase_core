# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The shrink-only per-file baseline of the first_party_ref runtime (OMN-21900)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.validation.model_first_party_tag_inventory_result import (
    ModelFirstPartyTagInventoryResult,
)
from omnibase_core.nodes.node_first_party_tag_inventory_effect.runtime_first_party_ref import (
    create_container,
    run,
)

pytestmark = pytest.mark.unit
TAG = "dev-20261018024445-b6ee996befa1"
SHA = "d7ed23f1" * 5
OTHER_SHA = "9218fe70" * 5
BASELINE = ".onex/baselines/first_party_ref.yaml"
WORKFLOW = ".github/workflows/ci.yml"


class MemoryInventory:
    def handle(self, request):
        return ModelFirstPartyTagInventoryResult(repo=request.repo, tags=(TAG,))


def write_workflow(root: Path, *refs: str) -> None:
    target = root / WORKFLOW
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(f"      - uses: OmniNode-ai/omnibase_core/x@{ref}\n" for ref in refs)
    )


def check(root: Path, *extra: str) -> int:
    return run(
        ["--root", str(root), "--baseline", BASELINE, *extra],
        container=create_container(MemoryInventory()),
    )


def test_baseline_is_generated_with_a_zero_target_note_and_no_suppression_marker(
    tmp_path,
):
    write_workflow(tmp_path, SHA)
    assert check(tmp_path, "--write-baseline") == 0
    text = (tmp_path / BASELINE).read_text()
    document = yaml.safe_load(text)
    assert document["hook"] == "first_party_ref"
    assert [(e["path"], e["rule"]) for e in document["entries"]] == [
        (WORKFLOW, "first_party_not_dev_tag")
    ]
    assert "Zero target" in text
    assert set(document) == {"schema_version", "hook", "entries"}
    assert set(document["entries"][0]) == {"path", "rule", "text"}
    assert "noqa" not in text.lower()
    assert check(tmp_path) == 0


def test_canary_adding_one_finding_to_a_baselined_file_is_refused(tmp_path, capsys):
    write_workflow(tmp_path, SHA)
    assert check(tmp_path, "--write-baseline") == 0
    write_workflow(tmp_path, SHA, OTHER_SHA)
    capsys.readouterr()
    assert check(tmp_path) == 1
    assert OTHER_SHA in capsys.readouterr().out


def test_identical_second_finding_in_a_baselined_file_is_refused(tmp_path):
    write_workflow(tmp_path, SHA)
    assert check(tmp_path, "--write-baseline") == 0
    write_workflow(tmp_path, SHA, SHA)
    assert check(tmp_path) == 1


def test_write_baseline_refuses_to_grow_and_leaves_the_file_unchanged(tmp_path):
    write_workflow(tmp_path, SHA)
    assert check(tmp_path, "--write-baseline") == 0
    before = (tmp_path / BASELINE).read_text()
    write_workflow(tmp_path, SHA, OTHER_SHA)
    assert check(tmp_path, "--write-baseline") == 1
    assert (tmp_path / BASELINE).read_text() == before


def test_a_fixed_finding_is_stale_until_the_baseline_shrinks(tmp_path):
    write_workflow(tmp_path, SHA, OTHER_SHA)
    assert check(tmp_path, "--write-baseline") == 0
    write_workflow(tmp_path, OTHER_SHA)
    assert check(tmp_path) == 1
    assert check(tmp_path, "--write-baseline") == 0
    document = yaml.safe_load((tmp_path / BASELINE).read_text())
    assert len(document["entries"]) == 1
    assert OTHER_SHA in document["entries"][0]["text"]
    assert check(tmp_path) == 0


def test_a_dev_tag_passes_with_an_empty_baseline_and_a_new_sha_does_not(tmp_path):
    write_workflow(tmp_path, TAG)
    assert check(tmp_path, "--write-baseline") == 0
    assert yaml.safe_load((tmp_path / BASELINE).read_text())["entries"] == []
    assert check(tmp_path) == 0
    write_workflow(tmp_path, TAG, SHA)
    assert check(tmp_path) == 1


def test_without_a_baseline_file_every_finding_fails(tmp_path):
    write_workflow(tmp_path, SHA)
    assert check(tmp_path) == 1


def test_write_baseline_needs_a_baseline_path(tmp_path):
    with pytest.raises(SystemExit):
        run(
            ["--root", str(tmp_path), "--write-baseline"],
            container=create_container(MemoryInventory()),
        )


def test_baseline_of_another_hook_is_refused(tmp_path):
    write_workflow(tmp_path, SHA)
    target = tmp_path / BASELINE
    target.parent.mkdir(parents=True)
    target.write_text("schema_version: 1\nhook: other\nentries: []\n")
    assert check(tmp_path) == 1

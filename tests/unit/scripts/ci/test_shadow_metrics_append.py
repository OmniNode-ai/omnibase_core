# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for the shadow-metrics NDJSON dedup-append (OMN-14342)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci.shadow_metrics_append import append_records

pytestmark = pytest.mark.unit


def _write_record(dirpath: Path, name: str, **fields: object) -> None:
    base = {"repo": "OmniNode-ai/omnibase_core", "head_sha": "sha1", "pr_number": 1}
    base.update(fields)
    (dirpath / name).write_text(json.dumps(base), encoding="utf-8")


def test_appends_new_record(tmp_path: Path) -> None:
    records = tmp_path / "records"
    records.mkdir()
    _write_record(records, "shadow_record.json", head_sha="abc", pr_number=7)
    ndjson = tmp_path / "shadow_metrics.ndjson"
    assert append_records(records, ndjson) == 1
    lines = ndjson.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["head_sha"] == "abc"


def test_dedup_is_idempotent(tmp_path: Path) -> None:
    records = tmp_path / "records"
    records.mkdir()
    _write_record(records, "shadow_record.json", head_sha="abc", pr_number=7)
    ndjson = tmp_path / "shadow_metrics.ndjson"
    assert append_records(records, ndjson) == 1
    # Second harvest of the same run appends nothing.
    assert append_records(records, ndjson) == 0
    assert len(ndjson.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_distinct_head_shas_both_appended(tmp_path: Path) -> None:
    records = tmp_path / "records"
    (records / "a").mkdir(parents=True)
    (records / "b").mkdir(parents=True)
    _write_record(records / "a", "shadow_record.json", head_sha="aaa", pr_number=1)
    _write_record(records / "b", "shadow_record.json", head_sha="bbb", pr_number=2)
    ndjson = tmp_path / "shadow_metrics.ndjson"
    assert append_records(records, ndjson) == 2


def test_malformed_record_skipped(tmp_path: Path) -> None:
    records = tmp_path / "records"
    records.mkdir()
    (records / "bad.json").write_text("{not json", encoding="utf-8")
    _write_record(records, "good.json", head_sha="ok", pr_number=3)
    ndjson = tmp_path / "shadow_metrics.ndjson"
    assert append_records(records, ndjson) == 1


def test_appended_line_is_canonical(tmp_path: Path) -> None:
    records = tmp_path / "records"
    records.mkdir()
    # keys deliberately out of order in the source file
    (records / "r.json").write_text(
        '{"pr_number": 9, "head_sha": "z", "repo": "r", "escaped_failure_count": 0}',
        encoding="utf-8",
    )
    ndjson = tmp_path / "shadow_metrics.ndjson"
    append_records(records, ndjson)
    line = ndjson.read_text(encoding="utf-8").strip()
    # sort_keys=True → keys alphabetical, stable regardless of source order
    assert line.startswith('{"escaped_failure_count": 0, "head_sha": "z"')

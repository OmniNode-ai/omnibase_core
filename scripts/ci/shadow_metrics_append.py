# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Append harvested shadow records to the ci-shadow-metrics NDJSON (OMN-14342).

Stage 2 of the durable store: dedup-append the per-run ``shadow_record.json``
artifacts into the append-only ``shadow_metrics.ndjson`` on the
``ci-shadow-metrics`` branch. Dedup key is (repo, head_sha, pr_number) so
re-harvesting the same CI run is idempotent. Extracted from the harvester
workflow so the append/dedup logic is unit-tested rather than inline shell.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _dedup_key(record: dict) -> tuple[object, object, object]:
    return (record.get("repo"), record.get("head_sha"), record.get("pr_number"))


def _load_existing_keys(ndjson: Path) -> set[tuple[object, object, object]]:
    keys: set[tuple[object, object, object]] = set()
    if not ndjson.exists():
        return keys
    for line in ndjson.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            keys.add(_dedup_key(json.loads(line)))
        except json.JSONDecodeError:
            continue
    return keys


def append_records(records_dir: Path, ndjson: Path) -> int:
    """Append not-yet-seen records from ``records_dir`` into ``ndjson``.

    Returns the number of records appended. Records are canonicalized
    (``sort_keys=True``) so the NDJSON line is stable regardless of field order.
    """
    seen = _load_existing_keys(ndjson)
    appended = 0
    lines: list[str] = []
    for path in sorted(records_dir.rglob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        key = _dedup_key(record)
        if key in seen:
            continue
        seen.add(key)
        lines.append(json.dumps(record, sort_keys=True))
        appended += 1
    if lines:
        with ndjson.open("a", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")
    return appended


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append shadow records to NDJSON")
    parser.add_argument("--records-dir", type=Path, required=True)
    parser.add_argument("--ndjson", type=Path, required=True)
    args = parser.parse_args(argv)
    count = append_records(args.records_dir, args.ndjson)
    sys.stdout.write(f"appended {count} new record(s)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

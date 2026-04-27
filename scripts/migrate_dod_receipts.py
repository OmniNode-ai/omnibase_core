#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI wrapper around :mod:`omnibase_core.utils.util_dod_receipt_migration`.

Usage:
    uv run python scripts/migrate_dod_receipts.py --root . [--dry-run]

The script walks ``drift/dod_receipts/`` and ``.evidence/`` under the given
root and rewrites any pre-OMN-9786 receipts into the extended
``ModelDodReceipt`` shape, downgrading their status to ``ADVISORY`` while
preserving the original status in ``original_status``. Idempotent.

This file intentionally contains no business logic — it exists so the
migration can be invoked as a one-off script (per OMN-9790 acceptance
criteria) without forcing every consumer to import the CLI plumbing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.utils.util_dod_receipt_migration import migrate_receipts_in_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill legacy DoD receipts into the OMN-9786 ModelDodReceipt "
            "schema, downgrading status to ADVISORY."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repo root containing drift/dod_receipts/ and/or .evidence/.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report counts without writing to disk.",
    )
    args = parser.parse_args(argv)

    modified, skipped = migrate_receipts_in_root(args.root, dry_run=args.dry_run)
    verb = "would migrate" if args.dry_run else "migrated"
    print(f"{verb}: {modified}, skipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Emit the canonical feature-flag catalog (OMN-7776).

Writes the env-independent registry declaration catalog to a committed JSON
artifact so cross-language consumers (the omnidash Express server) share the
single source of truth defined in :mod:`omnibase_core.feature_flags`.

Usage::

    uv run python scripts/gen_feature_flag_catalog.py
    uv run python scripts/gen_feature_flag_catalog.py --check   # drift gate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from omnibase_core.feature_flags import FEATURE_FLAG_REGISTRY

_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "omnibase_core"
    / "feature_flags"
    / "feature_flag_catalog.json"
)


def _render() -> str:
    payload = {
        "generated_by": "omnibase_core/scripts/gen_feature_flag_catalog.py",
        "ticket": "OMN-7776",
        "flags": FEATURE_FLAG_REGISTRY.static_catalog(),
    }
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=_DEFAULT_OUT, help="Output JSON path."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the on-disk artifact is stale instead of writing it.",
    )
    args = parser.parse_args()

    rendered = _render()
    if args.check:
        if not args.out.exists() or args.out.read_text(encoding="utf-8") != rendered:
            sys.stderr.write(
                f"feature flag catalog is stale: regenerate with "
                f"`uv run python {Path(__file__).name}`\n"
            )
            return 1
        return 0

    args.out.write_text(rendered, encoding="utf-8")
    sys.stdout.write(f"wrote {args.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

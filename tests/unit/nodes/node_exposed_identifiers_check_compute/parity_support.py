# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Synthetic corpus and salted digests."""

import hashlib
import json
from pathlib import Path

SYNTHETIC = "zz-synthetic-tenant-1"
FIXTURES = (
    Path(__file__).resolve().parents[4]
    / "tests/fixtures/validator_parity/exposed_identifiers"
)


def denylist_text() -> str:
    salt = "synthetic-parity-salt:"
    return json.dumps(
        {
            "salt": salt,
            "entries": [
                {
                    "id": f"synthetic-{index}",
                    "kind": "test-fixture",
                    "ticket": "OMN-20565",
                    "length": len(value),
                    "sha256": hashlib.sha256((salt + value).encode()).hexdigest(),
                }
                for index, value in enumerate((SYNTHETIC, SYNTHETIC[:12]))
            ],
        }
    )


def corpus() -> dict[str, str]:
    return json.loads((FIXTURES / "corpus.json").read_text())

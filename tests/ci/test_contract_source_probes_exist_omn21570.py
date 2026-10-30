# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Keep contract source comparisons pointing at files that exist after code moves.

Handler moves left OMN-17427 and OMN-19998 probes naming gone files, causing
dod-verify to fail on dev.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
CMP_SOURCE = re.compile(r"\|\s*cmp\s+-\s+(\S+?)'?(?:\s|$)")


def missing_cmp_sources(contract: object, root: Path) -> list[tuple[str, str]]:
    """Return evidence ids and missing tree paths named by source comparisons."""
    missing: list[tuple[str, str]] = []
    if not isinstance(contract, dict):
        return missing
    evidence = cast(dict[object, object], contract).get("dod_evidence")
    if not isinstance(evidence, list):
        return missing
    for item in cast(list[object], evidence):
        if not isinstance(item, dict):
            continue
        entry = cast(dict[object, object], item)
        evidence_id = entry.get("id")
        checks = entry.get("checks")
        if not isinstance(evidence_id, str) or not isinstance(checks, list):
            continue
        for check in cast(list[object], checks):
            if not isinstance(check, dict):
                continue
            check_value = cast(dict[object, object], check).get("check_value")
            if not isinstance(check_value, str):
                continue
            for match in CMP_SOURCE.finditer(check_value):
                path = match.group(1)
                if path.startswith(("src/", "tests/")) and not (root / path).is_file():
                    missing.append((evidence_id, path))
    return missing


def test_planted_probe_on_a_missing_file_is_reported(tmp_path: Path) -> None:
    contract = {
        "dod_evidence": [
            {
                "id": "planted-missing-source",
                "checks": [
                    {
                        "check_value": "bash -o pipefail -c 'curl ... | cmp - src/pkg/gone.py'",
                    },
                ],
            },
        ],
    }
    assert missing_cmp_sources(contract, tmp_path) == [
        ("planted-missing-source", "src/pkg/gone.py"),
    ]


def test_planted_probe_on_an_existing_file_is_not_reported(tmp_path: Path) -> None:
    source = tmp_path / "src/pkg/gone.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    contract = {
        "dod_evidence": [
            {
                "id": "planted-existing-source",
                "checks": [
                    {
                        "check_value": "bash -o pipefail -c 'curl ... | cmp - src/pkg/gone.py'",
                    },
                ],
            },
        ],
    }
    assert missing_cmp_sources(contract, tmp_path) == []


def test_planted_probe_with_no_dod_evidence_is_tolerated(tmp_path: Path) -> None:
    assert missing_cmp_sources({}, tmp_path) == []


def test_live_tree_every_contract_source_probe_names_an_existing_file() -> None:
    missing: list[tuple[str, str, str]] = []
    for contract_path in sorted((ROOT / "contracts").glob("OMN-*.yaml")):
        contract: object = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        missing.extend(
            (contract_path.name, evidence_id, path)
            for evidence_id, path in missing_cmp_sources(contract, ROOT)
        )
    assert missing == [], f"contract source probes name missing files: {missing}"

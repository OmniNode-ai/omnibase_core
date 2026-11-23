# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-26514: the ticket creation citation grammar and the history globs carry no ledger file name.

The two policy data files still named the ledger file in executable position: a citation regex and
two path globs. They match the work-ledger family spelling instead, and every spelling they matched
before still matches.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "src" / "omnibase_core" / "validation"
# The file name's own first word: the census counts the whole name, and the policy data must carry
# neither. The citations still matching the ledger file itself are held by
# test_ticket_creation_parity.py and test_hardcoded_model_config.py, which name it as test data.
NAME_WORD = "ROLLING"

CITATION = "docs/tracking/FAMILY_WORK_LEDGER.md:4120"
ARCHIVE_CITATION = "docs/tracking/archive/FAMILY_WORK_LEDGER_2026-10-12-split.md:7"


def _citation_patterns() -> list[str]:
    data = yaml.safe_load(
        (PACKAGE / "contracts" / "ticket_creation.validation.yaml").read_text(
            encoding="utf-8"
        )
    )
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "citation_patterns" and isinstance(value, list):
                    found.extend(str(item) for item in value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return found


def _history_globs() -> list[str]:
    data = yaml.safe_load(
        (PACKAGE / "hardcoded_model_config" / "policy.yaml").read_text(encoding="utf-8")
    )
    historical = next(c for c in data["path_classes"] if c["name"] == "HISTORICAL")
    return [str(glob) for glob in historical["globs"]]


def test_ledger_name_citation_patterns_carry_no_ledger_file_name() -> None:
    patterns = _citation_patterns()
    assert patterns
    assert [p for p in patterns if NAME_WORD in p] == []


def test_ledger_name_citation_patterns_match_the_family_spelling() -> None:
    patterns = [re.compile(p) for p in _citation_patterns()]
    for citation in (CITATION, ARCHIVE_CITATION):
        assert any(p.search(citation) for p in patterns), citation


def test_ledger_name_history_globs_carry_no_ledger_file_name() -> None:
    globs = _history_globs()
    assert globs
    assert [g for g in globs if NAME_WORD in g] == []


def test_ledger_name_history_globs_match_the_family_spelling() -> None:
    globs = _history_globs()
    for path in (
        "docs/tracking/FAMILY_WORK_LEDGER.md",
        "docs/tracking/archive/FAMILY_WORK_LEDGER_2026-10-12-split.md",
    ):
        # fnmatch has no ``**/`` segment form; the glob's leading ``**/`` also matches a path
        # with no directory part, so test the suffix form the policy classifier applies.
        assert any(fnmatch.fnmatch(path, glob.replace("**/", "*")) for glob in globs), (
            path
        )

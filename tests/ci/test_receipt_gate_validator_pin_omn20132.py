# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20132 - the Receipt Gate's validator checkout must know today's receipt shape.

``receipt-gate.yml`` checks out omnibase_core at a pinned sha to supply the
validator source. ModelDodReceipt forbids extra fields, so when the pin
predated ``tree_sha`` (omnibase_core#1748) every receipt written by current
tooling failed ``verify / verify`` with ``extra_forbidden``. This test reads
the pin, reads ModelDodReceipt at that exact sha, and asserts the floor of
fields the corpus already contains. Raise the floor when a new field starts
appearing in written receipts; the failure then names the pin to advance.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "receipt-gate.yml"
MODEL_PATH = "src/omnibase_core/models/contracts/ticket/model_dod_receipt.py"
CHECKOUT_PATH = ".receipt-gate-deps/omnibase_core"

# Fields receipts already carry in the wild. tree_sha: omnibase_core#1748.
REQUIRED_RECEIPT_FIELDS = frozenset({"tree_sha"})


def _pinned_validator_ref() -> str:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    refs: list[str] = []
    for job in data["jobs"].values():
        for step in job["steps"]:
            with_block = step.get("with") or {}
            if with_block.get("path") == CHECKOUT_PATH:
                refs.append(str(with_block["ref"]))
    assert len(refs) == 1, f"expected exactly one validator checkout, got {refs}"
    return refs[0]


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )


def _model_source_at(ref: str) -> str:
    shown = _git("show", f"{ref}:{MODEL_PATH}")
    if shown.returncode != 0:
        _git("fetch", "--depth=1", "origin", ref)
        shown = _git("show", f"{ref}:{MODEL_PATH}")
    if shown.returncode != 0:
        pytest.skip(f"validator ref {ref} is not reachable from this checkout")
    return shown.stdout


def _model_fields(source: str) -> set[str]:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ModelDodReceipt":
            return {
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            }
    raise AssertionError("ModelDodReceipt not found at the pinned validator ref")


def test_validator_ref_is_an_immutable_full_sha() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", _pinned_validator_ref())


def test_validator_ref_model_declares_every_required_receipt_field() -> None:
    ref = _pinned_validator_ref()
    missing = REQUIRED_RECEIPT_FIELDS - _model_fields(_model_source_at(ref))
    assert not missing, (
        f"receipt-gate.yml pins the validator at {ref}, whose ModelDodReceipt "
        f"lacks {sorted(missing)}; a receipt carrying them fails verify with "
        "extra_forbidden. Advance the validator ref in receipt-gate.yml, then "
        "every caller's call-receipt-gate.yml pin."
    )


def test_floor_holds_for_the_in_tree_model() -> None:
    """Positive control: the in-tree model has every field in the floor."""
    source = (REPO_ROOT / MODEL_PATH).read_text()
    assert _model_fields(source) >= REQUIRED_RECEIPT_FIELDS


def test_floor_rejects_the_pre_tree_sha_pin() -> None:
    """Positive control: the old pin, a03b10720db3, is below the floor."""
    old = "a03b10720db364575b0477003da95b46de765950"  # pragma: allowlist secret
    fields = _model_fields(_model_source_at(old))
    assert "tree_sha" not in fields

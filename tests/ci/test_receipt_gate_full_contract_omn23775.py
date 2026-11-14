# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-23775: the receipt-gate head verification passes dod-verify the full head
contract beside the scoped copy, and the workflow declares no Linear secret.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)


def _workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _head_verify_script() -> str:
    for step in _workflow()["jobs"]["dod-verify"]["steps"]:
        if step.get("id") == "head_verify":
            script = step["run"]
            assert isinstance(script, str)
            return script
    raise AssertionError("step head_verify not found in dod-verify")


def _walk(node: object, path: str = "") -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = [(path, node)]
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(_walk(key, f"{path}/<key>"))
            found.extend(_walk(value, f"{path}/{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_walk(value, f"{path}[{index}]"))
    return found


def test_full_contract_path_passed_to_head_dod_verify() -> None:
    script = _head_verify_script()
    invocation = re.search(
        r"node_dod_verify\s*\\\n(?P<args>(?:.*\\\n)*.*--output-path[^\n]*)", script
    )
    assert invocation is not None, "head dod-verify invocation not found"
    args = invocation.group("args")
    assert '--contract-path "$scoped"' in args
    # The unscoped head file, not the scoped copy and not the merge base's.
    assert '--full-contract-path "$contract"' in args
    assert 'contract="$head_tree/contracts/$ticket.yaml"' in script


def test_full_contract_path_not_the_scoped_copy() -> None:
    script = _head_verify_script()
    assert '--full-contract-path "$scoped"' not in script


def test_no_linear_secret_in_receipt_gate() -> None:
    # The header Secrets note records the OMN-23775 decision; the merge base lacks it.
    header = WORKFLOW_PATH.read_text().split("\nname: receipt-gate", 1)[0]
    assert "hosted CI holds no Linear" in " ".join(header.replace("#", " ").split())
    assert "OMN-23775" in header
    workflow = _workflow()
    # PyYAML reads the bare `on:` key as the boolean True.
    trigger = workflow.get("on", workflow.get(True))
    assert isinstance(trigger, dict)
    call = trigger["workflow_call"]
    assert "secrets" not in call, "receipt-gate must declare no workflow_call secret"
    assert "secrets" not in workflow
    offenders = [
        where
        for where, value in _walk(workflow)
        if isinstance(value, str)
        and (
            re.search(r"secrets\.[A-Za-z0-9_]*linear", value, re.IGNORECASE)
            or re.search(r"\bLINEAR_[A-Z_]*", value)
            or re.search(r"secrets:\s*inherit", value)
        )
    ]
    assert offenders == []
    assert "secrets" not in {
        key for job in workflow["jobs"].values() for key in job if key == "secrets"
    }

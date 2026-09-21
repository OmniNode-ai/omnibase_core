# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the deploy-gate action's standalone typed contract projection."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MODEL_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "actions"
    / "deploy-gate"
    / "models"
    / "deploy_evidence_contract.py"
)
sys.path.insert(0, str(_MODEL_PATH.parents[1]))
_SPEC = importlib.util.spec_from_file_location(
    "deploy_gate_evidence_contract", _MODEL_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
ModelDeployEvidenceContract = _MODULE.ModelDeployEvidenceContract


def test_contract_projects_deploy_evidence_and_ignores_other_contract_fields() -> None:
    contract = ModelDeployEvidenceContract.from_yaml(
        """
ticket_id: OMN-123
title: Runtime deployment
deploy_step: restart service
dod_evidence:
  - id: deploy
    description: Read back deployment evidence
    source: manual
    checks:
      - check_type: command
        check_value: docker exec runtime readback
"""
    )

    assert contract.dod_evidence[0].id == "deploy"
    assert contract.dod_evidence[0].checks[0].check_value == (
        "docker exec runtime readback"
    )


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        "ticket_id: 123\ndod_evidence: bad\n",
        "dod_evidence:\n  - id: deploy\n    unknown: true\n",
        "dod_evidence:\n  - id: deploy\n    description: text\n    source: manual\n    checks:\n      - check_type: command\n        check_value: run\n        unknown: true\n",
    ],
)
def test_contract_rejects_wrong_root_or_evidence_shape(content: str) -> None:
    with pytest.raises((ValueError, TypeError)):
        ModelDeployEvidenceContract.from_yaml(content)

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The caller verifier keeps the receipt gate on Python 3.13."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "receipt-gate.yml"
)


def test_workflow_uses_python_313() -> None:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    steps = data["jobs"]["dod-verify"]["steps"]
    setup = [
        s for s in steps if str(s.get("uses", "")).startswith("actions/setup-python@")
    ]
    assert len(setup) == 1
    assert setup[0]["name"] == "Set up Python 3.13"
    assert setup[0]["with"]["python-version"] == "3.13"
    assert "python-version-file" not in setup[0]["with"]
    assert "${{" not in setup[0]["with"]["python-version"]

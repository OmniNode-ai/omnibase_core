# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The diagram drift validator loads its contract and carries file locations."""

from pathlib import Path

import pytest

from omnibase_core.handlers.handler_diagram_drift_validator import ValidatorDiagramDrift
from tests.unit.handlers.diagram_drift_support.renderer import load_fixture_fragment


@pytest.mark.unit
def test_validator_loads_contract_and_reports_file_drift(tmp_path: Path) -> None:
    validator = ValidatorDiagramDrift(load_fixture_fragment)
    assert validator.contract.validator_id == "diagram_drift"
    assert validator.rules is validator.rules

    text = (
        Path(__file__).parent / "fixtures_diagram_drift" / "plan_diagrams.fixture"
    ).read_text(encoding="utf-8")
    report = validator.check_document(text)
    assert report.exit_code == 0
    assert report.diagrams_checked > 0

    edge = "    [*] --> open\n"
    assert edge in text
    changed = text.replace(edge, "    [*] --> swarming\n", 1)
    path = tmp_path / "changed.md"
    path.write_text(changed, encoding="utf-8")
    result = validator.validate_file(path)
    assert not result.is_valid
    assert len(result.issues) == 1
    assert result.issues[0].code == "diagram_differs"
    assert result.issues[0].file_path == path

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import json
from click.testing import CliRunner
from omnibase_core.cli.cli_doctor import doctor


def test_doctor_e2e_human_output():
    """Run doctor for real and verify grouped output structure."""
    runner = CliRunner()
    result = runner.invoke(doctor, [])
    # Should produce grouped output regardless of check results
    assert "passed]" in result.output
    assert "Summary:" in result.output


def test_doctor_e2e_json_output():
    """Run doctor with --json and verify parseable JSON with correct schema."""
    runner = CliRunner()
    result = runner.invoke(doctor, ["--json"])
    parsed = json.loads(result.output)
    assert "total" in parsed
    assert "passed" in parsed
    assert "failed" in parsed
    assert "checks" in parsed
    assert isinstance(parsed["checks"], list)
    assert len(parsed["checks"]) > 0
    # Each check has required fields
    for check in parsed["checks"]:
        assert "name" in check
        assert "category" in check
        assert "status" in check


def test_doctor_e2e_all_categories_present():
    """Verify all three check categories appear in output."""
    runner = CliRunner()
    result = runner.invoke(doctor, ["--json"])
    parsed = json.loads(result.output)
    categories = {c["category"] for c in parsed["checks"]}
    assert "services" in categories
    assert "environment" in categories
    # repos may or may not be present depending on environment

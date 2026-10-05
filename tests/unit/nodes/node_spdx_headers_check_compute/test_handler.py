# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""SPDX finding provenance, lexical eligibility, and input validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.cli.cli_spdx import is_spdx_eligible_path, validate_spdx_source
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.spdx_headers_check.model_spdx_headers_check_input import (
    ModelSpdxHeadersCheckInput,
)
from omnibase_core.nodes.node_spdx_headers_check_compute.handler import (
    VALIDATOR_ID,
    NodeSpdxHeadersCheckCompute,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("source", "line", "message"),
    [
        ("", 1, "File is empty (expected SPDX header)"),
        (
            "#!/bin/sh\n",
            1,
            "Missing SPDX header (file has only 1 lines)",
        ),
        (
            "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.\n",
            2,
            "Line 2: Missing '# SPDX-License-Identifier: MIT'",
        ),
    ],
)
def test_spdx_handler_findings(source: str, line: int, message: str) -> None:
    report = NodeSpdxHeadersCheckCompute().handle(
        ModelSpdxHeadersCheckInput(files=[ModelSourceFile(path="a.py", source=source)])
    )
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.validator_id == VALIDATOR_ID == "spdx-headers-check"
    assert finding.rule_id == "spdx-header"
    assert finding.severity == "FAIL"
    assert finding.location == f"a.py:{line}"
    assert finding.message == f"a.py: {message}"
    assert report.provenance.validators_run == (VALIDATOR_ID,)
    assert validate_spdx_source(source) == message


@pytest.mark.parametrize(
    ("path", "eligible"),
    [
        ("a.py", True),
        ("a.sh", True),
        ("a.bash", True),
        ("a.yml", True),
        ("a.yaml", True),
        ("a.toml", True),
        ("nested/Dockerfile", True),
        ("nested/Makefile", True),
        ("a.PY", False),
        ("a.txt", False),
        ("uv.lock", False),
        ("vendor/a.py", False),
        ("archive/a.py", False),
        ("archived/a.py", False),
        ("pkg.egg-info/a.py", False),
        (".venv/a.py", False),
        (".github/workflows/a.yml", True),
        ("schemas/a.yaml", True),
    ],
)
def test_spdx_eligibility_is_pure(
    path: str, eligible: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_filesystem(self: Path) -> bool:
        raise AssertionError("pure path predicate touched the filesystem")

    monkeypatch.setattr(Path, "is_file", no_filesystem)
    assert is_spdx_eligible_path(Path(path)) == eligible
    report = NodeSpdxHeadersCheckCompute().handle(
        ModelSpdxHeadersCheckInput(files=[ModelSourceFile(path=path, source="")])
    )
    assert bool(report.findings) == eligible


def test_spdx_input_frozen_and_extra_forbidden() -> None:
    request = ModelSpdxHeadersCheckInput()
    with pytest.raises(ValidationError):
        request.files = []
    with pytest.raises(ValidationError):
        ModelSpdxHeadersCheckInput.model_validate({"files": [], "unexpected": True})
    assert NodeSpdxHeadersCheckCompute().handle(request).overall_status == "PASS"

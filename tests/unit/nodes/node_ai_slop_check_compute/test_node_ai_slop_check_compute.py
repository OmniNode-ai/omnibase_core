# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Direct rule-matching parity and handler purity coverage."""

from pathlib import Path

import pytest

from omnibase_core.models.nodes.ai_slop_check.model_ai_slop_check_input import (
    ModelAiSlopCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_ai_slop_check_compute.handler import (
    NodeAiSlopCheckCompute,
)
from omnibase_core.validation.aislop_rule_loader import resolve_rules

from .parity_helpers import CORPUS, GOLDEN, ROOT, normalized_parity, rows_parity

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("name", sorted(CORPUS))
def test_parity_handler_rules(name: str) -> None:
    rules = resolve_rules(ROOT).rules
    report = NodeAiSlopCheckCompute().handle(
        ModelAiSlopCheckInput(
            files=[ModelSourceFile(path=name, source=CORPUS[name])],
            strict=True,
            report=True,
            rules=rules,
            fallback_docstring_rules=rules,
        )
    )
    assert normalized_parity(rows_parity(report)) == normalized_parity(
        GOLDEN[name]["1:1"]["findings"]
    )


def test_parity_handler_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    rules = resolve_rules(ROOT).rules

    def forbidden_read(self: Path, *args: object, **kwargs: object) -> str:
        pytest.fail("Handler attempted filesystem access")

    monkeypatch.setattr(Path, "read_text", forbidden_read)
    result = NodeAiSlopCheckCompute().handle(
        ModelAiSlopCheckInput(
            files=[ModelSourceFile(path="source.py", source=CORPUS["rest_param.py"])],
            rules=rules,
        )
    )
    assert result.overall_status == "FAIL"
    assert result.findings[0].rule_id == "rest_docstring"


@pytest.mark.parametrize("name", [".py", ".md", "source.PY", "source.txt"])
def test_parity_handler_unsupported_suffix(name: str) -> None:
    result = NodeAiSlopCheckCompute().handle(
        ModelAiSlopCheckInput(
            files=[ModelSourceFile(path=name, source=CORPUS["rest_param.py"])],
            rules=resolve_rules(ROOT).rules,
            strict=True,
            report=True,
        )
    )
    assert result.overall_status == "PASS"
    assert result.findings == ()

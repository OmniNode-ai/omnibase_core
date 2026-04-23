# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelTypeDebtPriority + ModelTypeDebtReport (ADK eval spike, P3)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_type_debt_priority import EnumTypeDebtPriority
from omnibase_core.models.quality.model_type_debt_priority import ModelTypeDebtPriority
from omnibase_core.models.quality.model_type_debt_report import ModelTypeDebtReport


def _priority(
    ref: str, pri: EnumTypeDebtPriority = EnumTypeDebtPriority.MAJOR
) -> ModelTypeDebtPriority:
    return ModelTypeDebtPriority(
        finding_ref=ref,
        priority=pri,
        rationale="because",
        fix_sketch=None,
    )


@pytest.mark.unit
class TestEnumTypeDebtPriority:
    def test_values(self) -> None:
        assert EnumTypeDebtPriority.CRITICAL.value == "critical"
        assert EnumTypeDebtPriority.MAJOR.value == "major"
        assert EnumTypeDebtPriority.MINOR.value == "minor"
        assert EnumTypeDebtPriority.NOISE.value == "noise"


@pytest.mark.unit
class TestModelTypeDebtPriority:
    def test_valid(self) -> None:
        p = ModelTypeDebtPriority(
            finding_ref="src/foo.py:12",
            priority=EnumTypeDebtPriority.CRITICAL,
            rationale="cascades into public API",
            fix_sketch="Replace Any with a concrete TypedDict",
        )
        assert p.priority == EnumTypeDebtPriority.CRITICAL
        assert p.fix_sketch is not None

    def test_frozen(self) -> None:
        p = _priority("src/foo.py:1")
        with pytest.raises(ValidationError):
            p.rationale = "changed"  # type: ignore[misc]


@pytest.mark.unit
class TestModelTypeDebtReport:
    def _report(self, **overrides: object) -> ModelTypeDebtReport:
        defaults: dict[str, object] = {
            "repo": "omnibase_core",
            "generated_at": datetime(2026, 4, 23, 16, 0, 0, tzinfo=UTC),
            "findings_total": 5,
            "findings_prioritized": [
                _priority("src/a.py:1"),
                _priority("src/a.py:2"),
                _priority("src/a.py:3"),
            ],
            "tool": "omnimarket_node",
            "latency_seconds": 4.2,
            "llm_calls": 1,
            "estimated_cost_usd": 0.0,
        }
        defaults.update(overrides)
        return ModelTypeDebtReport(**defaults)  # type: ignore[arg-type]

    def test_valid(self) -> None:
        r = self._report()
        assert r.tool == "omnimarket_node"
        assert len(r.findings_prioritized) == 3

    def test_tool_literal(self) -> None:
        r = self._report(tool="adk")
        assert r.tool == "adk"
        with pytest.raises(ValidationError):
            self._report(tool="bogus")

    def test_negative_cost_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._report(estimated_cost_usd=-0.01)

    def test_negative_latency_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._report(latency_seconds=-1.0)

    def test_negative_llm_calls_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._report(llm_calls=-1)

    def test_duplicate_finding_ref_rejected(self) -> None:
        dupe = [
            _priority("src/a.py:1"),
            _priority("src/a.py:1"),
        ]
        with pytest.raises(ValidationError):
            self._report(findings_prioritized=dupe)

    def test_frozen(self) -> None:
        r = self._report()
        with pytest.raises(ValidationError):
            r.repo = "other"  # type: ignore[misc]

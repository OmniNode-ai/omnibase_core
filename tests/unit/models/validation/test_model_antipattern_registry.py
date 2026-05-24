# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelAntipatternEntry and ModelAntipatternRegistry (OMN-11910)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.models.validation.model_antipattern_entry import (
    ModelAntipatternEntry,
)
from omnibase_core.models.validation.model_antipattern_example import (
    ModelAntipatternExample,
)
from omnibase_core.models.validation.model_antipattern_registry import (
    ModelAntipatternRegistry,
)


def _make_entry(**overrides: object) -> ModelAntipatternEntry:
    defaults: dict[str, object] = {
        "name": "no_bare_except",
        "severity": "ERROR",
        "enforcement": "blocking",
        "category": "code_quality",
        "pattern_type": "regex_line",
        "pattern": r"except\s*:",
        "file_globs": ("*.py",),
        "suppression_annotation": "antipattern-ok",
        "description": "Bare except clauses swallow all exceptions",
        "rationale": "Masks errors and makes debugging impossible",
        "examples": (),
        "discovered_date": date(2025, 1, 15),
        "source_ticket": "OMN-11910",
        "vector_enabled": False,
    }
    defaults.update(overrides)
    return ModelAntipatternEntry(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelAntipatternExample:
    def test_basic_example(self) -> None:
        ex = ModelAntipatternExample(
            kind="bad",
            code="except:\n    pass",
            label="Bare except",
        )
        assert ex.kind == "bad"
        assert ex.label == "Bare except"

    def test_kind_literal_validation(self) -> None:
        with pytest.raises(ValidationError):
            ModelAntipatternExample(
                kind="unknown",  # type: ignore[arg-type]
                code="x",
                label="bad kind",
            )

    def test_example_roundtrip(self) -> None:
        ex = ModelAntipatternExample(
            kind="good", code="except ValueError:\n    pass", label="Typed except"
        )
        assert ModelAntipatternExample.model_validate(ex.model_dump()) == ex


@pytest.mark.unit
class TestModelAntipatternEntry:
    def test_minimal_entry(self) -> None:
        entry = _make_entry()
        assert entry.name == "no_bare_except"
        assert entry.severity == "ERROR"
        assert entry.enforcement == "blocking"
        assert entry.category == "code_quality"
        assert entry.pattern_type == "regex_line"
        assert entry.vector_enabled is False
        assert isinstance(entry.file_globs, tuple)
        assert isinstance(entry.examples, tuple)

    def test_invalid_severity_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_entry(severity="FATAL")  # type: ignore[arg-type]

    def test_invalid_enforcement_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_entry(enforcement="required")  # type: ignore[arg-type]

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_entry(category="style")  # type: ignore[arg-type]

    def test_invalid_pattern_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_entry(pattern_type="unknown")  # type: ignore[arg-type]

    def test_semantic_pattern_type_requires_vector_enabled(self) -> None:
        """pattern_type=semantic must have vector_enabled=True."""
        with pytest.raises(ValidationError, match="vector_enabled"):
            _make_entry(pattern_type="semantic", vector_enabled=False)

    def test_semantic_pattern_type_with_vector_enabled_passes(self) -> None:
        entry = _make_entry(pattern_type="semantic", vector_enabled=True)
        assert entry.pattern_type == "semantic"
        assert entry.vector_enabled is True

    def test_semantic_defaults_to_advisory(self) -> None:
        """Semantic antipatterns default to enforcement=advisory."""
        entry = _make_entry(
            pattern_type="semantic", vector_enabled=True, enforcement="advisory"
        )
        assert entry.enforcement == "advisory"

    def test_entry_is_frozen(self) -> None:
        entry = _make_entry()
        with pytest.raises(Exception):
            entry.name = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            _make_entry(unknown_field="x")  # type: ignore[call-arg]

    def test_entry_dict_roundtrip(self) -> None:
        entry = _make_entry()
        restored = ModelAntipatternEntry.model_validate(entry.model_dump())
        assert restored == entry

    def test_entry_yaml_roundtrip(self) -> None:
        entry = _make_entry()
        data = entry.model_dump(mode="json")
        yaml_str = yaml.dump(data, default_flow_style=False)
        restored_data = yaml.safe_load(yaml_str)
        restored = ModelAntipatternEntry.model_validate(restored_data)
        assert restored == entry

    def test_entry_with_examples(self) -> None:
        examples = (
            ModelAntipatternExample(kind="bad", code="except:\n    pass", label="Bare"),
            ModelAntipatternExample(
                kind="good", code="except ValueError:\n    pass", label="Typed"
            ),
        )
        entry = _make_entry(examples=examples)
        assert len(entry.examples) == 2
        assert entry.examples[0].kind == "bad"

    def test_source_ticket_format(self) -> None:
        entry = _make_entry(source_ticket="OMN-99999")
        assert entry.source_ticket == "OMN-99999"


@pytest.mark.unit
class TestModelAntipatternRegistry:
    def _make_registry(self, **overrides: object) -> ModelAntipatternRegistry:
        defaults: dict[str, object] = {
            "version": "1.0.0",
            "last_updated": datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            "entries": (_make_entry(),),
        }
        defaults.update(overrides)
        return ModelAntipatternRegistry(**defaults)  # type: ignore[arg-type]

    def test_basic_registry(self) -> None:
        reg = self._make_registry()
        assert reg.version == "1.0.0"
        assert len(reg.entries) == 1
        assert isinstance(reg.entries, tuple)

    def test_registry_is_frozen(self) -> None:
        reg = self._make_registry()
        with pytest.raises(Exception):
            reg.version = "2.0.0"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            self._make_registry(unknown="x")  # type: ignore[call-arg]

    def test_empty_entries(self) -> None:
        reg = self._make_registry(entries=())
        assert len(reg.entries) == 0

    def test_multiple_entries(self) -> None:
        entries = (
            _make_entry(name="rule_a"),
            _make_entry(name="rule_b"),
        )
        reg = self._make_registry(entries=entries)
        assert len(reg.entries) == 2

    def test_registry_dict_roundtrip(self) -> None:
        reg = self._make_registry()
        restored = ModelAntipatternRegistry.model_validate(reg.model_dump())
        assert restored == reg

    def test_registry_yaml_roundtrip(self) -> None:
        reg = self._make_registry()
        data = reg.model_dump(mode="json")
        yaml_str = yaml.dump(data, default_flow_style=False)
        restored_data = yaml.safe_load(yaml_str)
        restored = ModelAntipatternRegistry.model_validate(restored_data)
        assert restored == reg

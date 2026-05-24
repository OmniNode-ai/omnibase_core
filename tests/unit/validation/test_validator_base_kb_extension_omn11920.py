# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ValidatorBase KB-aware extension (OMN-11920).

Covers acceptance criteria:
- ValidatorBase.__init__ accepts optional antipattern_registry (default None, backward compatible)
- _validate_file_against_kb_rules() returns tuple[ModelValidationIssue, ...]
- Pattern matching for regex_line and grep_code entries
- Suppression annotations from registry entries honored
- No changes to existing validator subclasses (backward compat)
- Every validation result records: antipattern_registry_version, antipattern_registry_hash,
  rule_ids_applied, validator_version
- Validation results reproducible given same registry version and input
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_antipattern_entry import (
    ModelAntipatternEntry,
)
from omnibase_core.models.validation.model_antipattern_registry import (
    ModelAntipatternRegistry,
)
from omnibase_core.validation.validator_base import ValidatorBase

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_entry(
    name: str,
    pattern: str,
    pattern_type: str = "regex_line",
    severity: str = "ERROR",
    suppression_annotation: str = "antipattern-ok",
    file_globs: tuple[str, ...] = ("*.py",),
) -> ModelAntipatternEntry:
    return ModelAntipatternEntry(
        name=name,
        severity=severity,  # type: ignore[arg-type]
        enforcement="blocking",
        category="code_quality",
        pattern_type=pattern_type,  # type: ignore[arg-type]
        pattern=pattern,
        file_globs=file_globs,
        suppression_annotation=suppression_annotation,
        description=f"Test entry {name}",
        rationale="Test rationale",
        discovered_date="2026-01-01",  # type: ignore[arg-type]
        source_ticket="OMN-11920",
    )


def _make_registry(
    entries: tuple[ModelAntipatternEntry, ...] = (),
    version: str = "1.0.0",
) -> ModelAntipatternRegistry:
    return ModelAntipatternRegistry(
        version=version,
        last_updated=datetime(2026, 5, 24, tzinfo=UTC),
        entries=entries,
    )


def _make_contract() -> ModelValidatorSubcontract:
    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id="test_kb_validator",
        validator_name="Test KB Validator",
        validator_description="Test",
        target_patterns=["**/*.py"],
        exclude_patterns=[],
        suppression_comments=["# noqa:"],
        fail_on_error=True,
        fail_on_warning=False,
        max_violations=0,
        severity_default=EnumSeverity.ERROR,
    )


class ConcreteKBValidator(ValidatorBase):
    """Minimal concrete subclass for testing KB extension."""

    validator_id: ClassVar[str] = "concrete_kb_validator"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        return ()


# ---------------------------------------------------------------------------
# Test: backward compatibility — no registry param
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidatorBaseKBBackwardCompat:
    def test_init_without_registry_still_works(self) -> None:
        contract = _make_contract()
        validator = ConcreteKBValidator(contract=contract)
        assert validator.antipattern_registry is None

    def test_validate_file_against_kb_rules_with_no_registry_returns_empty(
        self, tmp_path: Path
    ) -> None:
        contract = _make_contract()
        validator = ConcreteKBValidator(contract=contract)
        target = tmp_path / "test.py"
        target.write_text("x = 1\n")
        result = validator._validate_file_against_kb_rules(target)
        assert result == ()

    def test_validate_runs_without_registry(self, tmp_path: Path) -> None:
        contract = _make_contract()
        validator = ConcreteKBValidator(contract=contract)
        target = tmp_path / "test.py"
        target.write_text("x = 1\n")
        result = validator.validate(target)
        assert result.is_valid


# ---------------------------------------------------------------------------
# Test: constructor accepts registry
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidatorBaseKBConstructor:
    def test_init_with_registry_stores_it(self) -> None:
        registry = _make_registry()
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )
        assert validator.antipattern_registry is registry

    def test_registry_is_none_by_default(self) -> None:
        contract = _make_contract()
        validator = ConcreteKBValidator(contract=contract)
        assert validator.antipattern_registry is None


# ---------------------------------------------------------------------------
# Test: _validate_file_against_kb_rules — regex_line matching
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateFileAgainstKBRules:
    def test_regex_line_match_returns_issue(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="test_rule",
            pattern=r"hardcoded_secret\s*=",
            pattern_type="regex_line",
            severity="ERROR",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        target.write_text("hardcoded_secret = 'abc'\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert len(issues) == 1
        assert issues[0].rule_name == "test_rule"
        assert issues[0].severity == EnumSeverity.ERROR

    def test_regex_line_no_match_returns_empty(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="test_rule",
            pattern=r"hardcoded_secret\s*=",
            pattern_type="regex_line",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        target.write_text("x = 1\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert issues == ()

    def test_grep_code_match_returns_issue(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="hardcoded_ip_rule",
            pattern=r"\b192\.168\.\d+\.\d+\b",
            pattern_type="grep_code",
            severity="ERROR",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        target.write_text('HOST = "192.168.1.100"\n')

        issues = validator._validate_file_against_kb_rules(target)
        assert len(issues) == 1
        assert issues[0].rule_name == "hardcoded_ip_rule"

    def test_multiple_matching_lines_produces_multiple_issues(
        self, tmp_path: Path
    ) -> None:
        entry = _make_entry(
            name="test_rule",
            pattern=r"BAD_PATTERN",
            pattern_type="regex_line",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        target.write_text("BAD_PATTERN = 1\nBAD_PATTERN = 2\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert len(issues) == 2

    def test_issue_has_correct_file_path_and_line_number(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="test_rule",
            pattern=r"BAD",
            pattern_type="regex_line",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        target.write_text("good\nBAD\ngood\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert len(issues) == 1
        assert issues[0].line_number == 2
        assert issues[0].file_path == target

    def test_warning_severity_entry_maps_correctly(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="warn_rule",
            pattern=r"WARNING_PATTERN",
            pattern_type="regex_line",
            severity="WARNING",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        target.write_text("WARNING_PATTERN\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert len(issues) == 1
        assert issues[0].severity == EnumSeverity.WARNING

    def test_info_severity_entry_maps_correctly(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="info_rule",
            pattern=r"INFO_PATTERN",
            pattern_type="regex_line",
            severity="INFO",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        target.write_text("INFO_PATTERN\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert len(issues) == 1
        assert issues[0].severity == EnumSeverity.INFO


# ---------------------------------------------------------------------------
# Test: file_globs filtering
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateFileAgainstKBRulesGlobFiltering:
    def test_entry_only_applies_to_matching_globs(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="py_only",
            pattern=r"BAD",
            pattern_type="grep_code",
            file_globs=("*.py",),
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        # .yaml file should NOT be checked by this entry
        target = tmp_path / "config.yaml"
        target.write_text("BAD: value\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert issues == ()

    def test_entry_applies_when_glob_matches(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="yaml_rule",
            pattern=r"BAD",
            pattern_type="grep_code",
            file_globs=("*.yaml",),
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "config.yaml"
        target.write_text("BAD: value\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# Test: suppression annotations
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateFileAgainstKBRulesSuppressionAnnotations:
    def test_suppression_annotation_suppresses_issue(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="test_rule",
            pattern=r"BAD",
            pattern_type="regex_line",
            suppression_annotation="antipattern-ok",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        target.write_text("BAD  # antipattern-ok\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert issues == ()

    def test_suppression_only_applies_to_same_line(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="test_rule",
            pattern=r"BAD",
            pattern_type="regex_line",
            suppression_annotation="antipattern-ok",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        # First line suppressed, second line not
        target.write_text("BAD  # antipattern-ok\nBAD\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert len(issues) == 1
        assert issues[0].line_number == 2

    def test_different_suppression_annotation_does_not_suppress(
        self, tmp_path: Path
    ) -> None:
        entry = _make_entry(
            name="test_rule",
            pattern=r"BAD",
            pattern_type="regex_line",
            suppression_annotation="my-specific-ok",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        # Wrong suppression annotation — should NOT suppress
        target.write_text("BAD  # antipattern-ok\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# Test: semantic entries are skipped (not applicable for regex matching)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateFileAgainstKBRulesSemanticSkip:
    def test_semantic_entry_is_skipped(self, tmp_path: Path) -> None:
        entry = ModelAntipatternEntry(
            name="semantic_entry",
            severity="ERROR",
            enforcement="blocking",
            category="architecture",
            pattern_type="semantic",
            pattern="some semantic description",
            file_globs=("*.py",),
            suppression_annotation="antipattern-ok",
            description="Semantic test entry",
            rationale="Test",
            discovered_date="2026-01-01",  # type: ignore[arg-type]
            source_ticket="OMN-11920",
            vector_enabled=True,
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        target.write_text("some semantic description\n")

        # Semantic entries require vector search — not applicable here
        issues = validator._validate_file_against_kb_rules(target)
        assert issues == ()

    def test_ast_check_entry_is_skipped(self, tmp_path: Path) -> None:
        # ast_check entries can't be run via regex — should be skipped
        entry = ModelAntipatternEntry(
            name="ast_entry",
            severity="ERROR",
            enforcement="blocking",
            category="code_quality",
            pattern_type="ast_check",
            pattern="some_ast_identifier",
            file_globs=("*.py",),
            suppression_annotation="antipattern-ok",
            description="AST test entry",
            rationale="Test",
            discovered_date="2026-01-01",  # type: ignore[arg-type]
            source_ticket="OMN-11920",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()
        validator = ConcreteKBValidator(
            contract=contract, antipattern_registry=registry
        )

        target = tmp_path / "test.py"
        target.write_text("some_ast_identifier\n")

        issues = validator._validate_file_against_kb_rules(target)
        assert issues == ()


# ---------------------------------------------------------------------------
# Test: result metadata fields (registry version, hash, rule_ids_applied)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidatorBaseKBResultMetadata:
    def _make_validator_with_registry(
        self, registry: ModelAntipatternRegistry
    ) -> ConcreteKBValidator:
        contract = _make_contract()
        return ConcreteKBValidator(contract=contract, antipattern_registry=registry)

    def test_result_metadata_contains_registry_version(self, tmp_path: Path) -> None:
        registry = _make_registry(version="2.3.4")
        validator = self._make_validator_with_registry(registry)
        target = tmp_path / "test.py"
        target.write_text("x = 1\n")

        result = validator.validate(target)
        assert result.metadata is not None
        assert result.metadata.model_extra is not None
        assert (
            result.metadata.model_extra.get("antipattern_registry_version") == "2.3.4"
        )

    def test_result_metadata_contains_registry_hash(self, tmp_path: Path) -> None:
        registry = _make_registry(version="1.0.0")
        validator = self._make_validator_with_registry(registry)
        target = tmp_path / "test.py"
        target.write_text("x = 1\n")

        result = validator.validate(target)
        assert result.metadata is not None
        assert result.metadata.model_extra is not None
        registry_hash = result.metadata.model_extra.get("antipattern_registry_hash")
        assert registry_hash is not None
        assert isinstance(registry_hash, str)
        assert len(registry_hash) == 64  # SHA-256 hex digest

    def test_result_metadata_contains_rule_ids_applied(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="test_rule",
            pattern=r"BAD",
            pattern_type="regex_line",
        )
        registry = _make_registry(entries=(entry,))
        validator = self._make_validator_with_registry(registry)
        target = tmp_path / "test.py"
        target.write_text("x = 1\n")

        result = validator.validate(target)
        assert result.metadata is not None
        assert result.metadata.model_extra is not None
        rule_ids = result.metadata.model_extra.get("rule_ids_applied")
        assert rule_ids is not None
        assert "test_rule" in rule_ids

    def test_result_without_registry_does_not_add_registry_fields(
        self, tmp_path: Path
    ) -> None:
        contract = _make_contract()
        validator = ConcreteKBValidator(contract=contract)
        target = tmp_path / "test.py"
        target.write_text("x = 1\n")

        result = validator.validate(target)
        assert result.metadata is not None
        # Without registry, no antipattern metadata fields should be set
        extra = result.metadata.model_extra or {}
        assert "antipattern_registry_version" not in extra
        assert "antipattern_registry_hash" not in extra

    def test_registry_hash_is_deterministic(self, tmp_path: Path) -> None:
        registry = _make_registry(version="1.0.0")
        validator1 = self._make_validator_with_registry(registry)
        validator2 = self._make_validator_with_registry(registry)

        target = tmp_path / "test.py"
        target.write_text("x = 1\n")

        result1 = validator1.validate(target)
        result2 = validator2.validate(target)

        assert result1.metadata is not None
        assert result2.metadata is not None
        assert result1.metadata.model_extra is not None
        assert result2.metadata.model_extra is not None
        hash1 = result1.metadata.model_extra.get("antipattern_registry_hash")
        hash2 = result2.metadata.model_extra.get("antipattern_registry_hash")
        assert hash1 == hash2


# ---------------------------------------------------------------------------
# Test: reproducibility
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidatorBaseKBReproducibility:
    def test_same_input_produces_same_issues(self, tmp_path: Path) -> None:
        entry = _make_entry(
            name="test_rule",
            pattern=r"BAD",
            pattern_type="regex_line",
        )
        registry = _make_registry(entries=(entry,))
        contract = _make_contract()

        target = tmp_path / "test.py"
        target.write_text("BAD\nBAD\n")

        v1 = ConcreteKBValidator(contract=contract, antipattern_registry=registry)
        v2 = ConcreteKBValidator(contract=contract, antipattern_registry=registry)

        issues1 = v1._validate_file_against_kb_rules(target)
        issues2 = v2._validate_file_against_kb_rules(target)

        assert len(issues1) == len(issues2)
        for i1, i2 in zip(issues1, issues2, strict=True):
            assert i1.rule_name == i2.rule_name
            assert i1.line_number == i2.line_number
            assert i1.severity == i2.severity

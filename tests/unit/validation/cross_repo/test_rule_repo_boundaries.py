# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for repo_boundaries rule.

Related ticket: OMN-1771
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleRepoBoundariesConfig,
)
from omnibase_core.validation.cross_repo.rules.rule_repo_boundaries import (
    RuleRepoBoundaries,
)
from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
    ModelImportInfo,
    ScannerImportGraph,
)

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "cross_repo_validation"
)


class TestRuleRepoBoundaries:
    """Tests for RuleRepoBoundaries."""

    @pytest.fixture
    def config(self) -> ModelRuleRepoBoundariesConfig:
        """Create a test configuration."""
        return ModelRuleRepoBoundariesConfig(
            enabled=True,
            severity=EnumSeverity.ERROR,
            ownership={
                "fake_core.": "fake_core",
                "fake_infra.": "fake_infra",
                "fake_app.": "fake_app",
            },
            forbidden_import_prefixes=[
                "fake_infra.services",
                "fake_core.internal",
            ],
            allowed_cross_repo_prefixes=[
                "fake_core.protocols",
                "fake_infra.protocols",
            ],
        )

    def test_detects_forbidden_import(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test that forbidden imports are detected."""
        rule = RuleRepoBoundaries(config)

        # Create mock import data
        file_imports = {
            Path("/test/bad.py"): ModelFileImports(
                file_path=Path("/test/bad.py"),
                imports=(
                    ModelImportInfo(
                        module="fake_infra.services.service_kafka",
                        line_number=1,
                        is_from_import=False,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 1
        assert issues[0].code == "CROSS_REPO_FORBIDDEN_IMPORT"
        assert "fake_infra.services" in issues[0].message

    def test_allows_valid_cross_repo_import(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test that allowed cross-repo imports pass."""
        rule = RuleRepoBoundaries(config)

        file_imports = {
            Path("/test/good.py"): ModelFileImports(
                file_path=Path("/test/good.py"),
                imports=(
                    ModelImportInfo(
                        module="fake_infra.protocols.protocol_bar",
                        line_number=1,
                        is_from_import=False,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 0

    def test_disabled_rule_returns_no_issues(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test that disabled rules don't report issues."""
        disabled_config = ModelRuleRepoBoundariesConfig(
            enabled=False,
            ownership=config.ownership,
            forbidden_import_prefixes=config.forbidden_import_prefixes,
        )
        rule = RuleRepoBoundaries(disabled_config)

        file_imports = {
            Path("/test/bad.py"): ModelFileImports(
                file_path=Path("/test/bad.py"),
                imports=(
                    ModelImportInfo(
                        module="fake_infra.services.kafka",
                        line_number=1,
                        is_from_import=False,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 0

    def test_from_import_forbidden(self, config: ModelRuleRepoBoundariesConfig) -> None:
        """Test that from-style imports are also checked."""
        rule = RuleRepoBoundaries(config)

        file_imports = {
            Path("/test/bad.py"): ModelFileImports(
                file_path=Path("/test/bad.py"),
                imports=(
                    ModelImportInfo(
                        module="fake_infra.services.service_kafka",
                        name="ServiceKafka",
                        line_number=5,
                        is_from_import=True,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 1
        assert issues[0].line_number == 5

    def test_cross_repo_boundary_violation(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test detection of cross-repo boundary violations."""
        rule = RuleRepoBoundaries(config)

        # Importing from fake_infra but NOT from protocols (not allowed)
        file_imports = {
            Path("/test/bad.py"): ModelFileImports(
                file_path=Path("/test/bad.py"),
                imports=(
                    ModelImportInfo(
                        module="fake_infra.models.some_model",
                        line_number=1,
                        is_from_import=False,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        # Should detect boundary violation (not in allowed prefixes)
        assert len(issues) == 1
        assert issues[0].code == "CROSS_REPO_BOUNDARY_VIOLATION"

    def test_same_repo_import_allowed(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test that imports within same repo are allowed."""
        rule = RuleRepoBoundaries(config)

        file_imports = {
            Path("/test/good.py"): ModelFileImports(
                file_path=Path("/test/good.py"),
                imports=(
                    ModelImportInfo(
                        module="fake_app.handlers.some_handler",
                        line_number=1,
                        is_from_import=False,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 0

    def test_parse_error_reported_as_warning(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test that parse errors are reported as warnings."""
        rule = RuleRepoBoundaries(config)

        file_imports = {
            Path("/test/bad_syntax.py"): ModelFileImports(
                file_path=Path("/test/bad_syntax.py"),
                parse_error="Syntax error at line 5",
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 1
        assert issues[0].severity == EnumSeverity.WARNING
        assert "Could not parse" in issues[0].message

    def test_relative_imports_skipped(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test that relative imports are skipped."""
        rule = RuleRepoBoundaries(config)

        file_imports = {
            Path("/test/good.py"): ModelFileImports(
                file_path=Path("/test/good.py"),
                imports=(
                    ModelImportInfo(
                        module="",
                        name="helper",
                        line_number=1,
                        is_from_import=True,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 0

    def test_stdlib_imports_not_flagged(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test that standard library imports are not flagged."""
        rule = RuleRepoBoundaries(config)

        file_imports = {
            Path("/test/good.py"): ModelFileImports(
                file_path=Path("/test/good.py"),
                imports=(
                    ModelImportInfo(
                        module="os",
                        line_number=1,
                        is_from_import=False,
                    ),
                    ModelImportInfo(
                        module="pathlib",
                        name="Path",
                        line_number=2,
                        is_from_import=True,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 0

    def test_with_real_fixtures(self) -> None:
        """Test against real fixture files."""
        config = ModelRuleRepoBoundariesConfig(
            enabled=True,
            severity=EnumSeverity.ERROR,
            ownership={
                "fake_core.": "fake_core",
                "fake_infra.": "fake_infra",
                "fake_app.": "fake_app",
            },
            forbidden_import_prefixes=[
                "fake_infra.services",
                "fake_core.internal",
            ],
            allowed_cross_repo_prefixes=[
                "fake_core.protocols",
                "fake_infra.protocols",
            ],
        )

        rule = RuleRepoBoundaries(config)
        scanner = ScannerImportGraph()

        # Scan the bad_handler.py file
        bad_handler = FIXTURES_DIR / "fake_app" / "src" / "fake_app" / "bad_handler.py"
        if bad_handler.exists():
            file_imports = {bad_handler: scanner.scan_file(bad_handler)}
            issues = rule.validate(file_imports, "fake_app")

            # Should detect the forbidden import
            assert len(issues) >= 1
            assert any("fake_infra.services" in str(i.message) for i in issues)

    def test_issue_contains_context(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test that issues include context information."""
        rule = RuleRepoBoundaries(config)

        file_imports = {
            Path("/test/bad.py"): ModelFileImports(
                file_path=Path("/test/bad.py"),
                imports=(
                    ModelImportInfo(
                        module="fake_infra.services.service_kafka",
                        line_number=10,
                        is_from_import=False,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 1
        assert issues[0].context is not None
        assert issues[0].context.get("import") == "fake_infra.services.service_kafka"
        assert issues[0].context.get("forbidden_prefix") == "fake_infra.services"

    def test_issue_contains_fingerprint_and_symbol(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test that issues include fingerprint and symbol for baseline tracking."""
        rule = RuleRepoBoundaries(config)

        file_imports = {
            Path("/test/bad.py"): ModelFileImports(
                file_path=Path("/test/bad.py"),
                imports=(
                    ModelImportInfo(
                        module="fake_infra.services.service_kafka",
                        line_number=10,
                        is_from_import=False,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 1
        assert issues[0].context is not None

        # Verify symbol is present (the import path that triggered violation)
        assert issues[0].context.get("symbol") == "fake_infra.services.service_kafka"

        # Verify fingerprint is present and has correct format (16 hex chars)
        fingerprint = issues[0].context.get("fingerprint")
        assert fingerprint is not None
        assert len(fingerprint) == 16
        assert all(c in "0123456789abcdef" for c in fingerprint)

    def test_boundary_violation_contains_fingerprint_and_symbol(
        self, config: ModelRuleRepoBoundariesConfig
    ) -> None:
        """Test that boundary violations include fingerprint and symbol."""
        rule = RuleRepoBoundaries(config)

        # Import from fake_infra but NOT from protocols (causes boundary violation)
        file_imports = {
            Path("/test/cross_repo.py"): ModelFileImports(
                file_path=Path("/test/cross_repo.py"),
                imports=(
                    ModelImportInfo(
                        module="fake_infra.models.some_model",
                        line_number=5,
                        is_from_import=False,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 1
        assert issues[0].code == "CROSS_REPO_BOUNDARY_VIOLATION"
        assert issues[0].context is not None

        # Verify symbol and fingerprint
        assert issues[0].context.get("symbol") == "fake_infra.models.some_model"
        fingerprint = issues[0].context.get("fingerprint")
        assert fingerprint is not None
        assert len(fingerprint) == 16

    def test_issue_has_suggestion(self, config: ModelRuleRepoBoundariesConfig) -> None:
        """Test that issues include suggestions."""
        rule = RuleRepoBoundaries(config)

        file_imports = {
            Path("/test/bad.py"): ModelFileImports(
                file_path=Path("/test/bad.py"),
                imports=(
                    ModelImportInfo(
                        module="fake_infra.services.service_kafka",
                        line_number=1,
                        is_from_import=False,
                    ),
                ),
            ),
        }

        issues = rule.validate(file_imports, "fake_app")

        assert len(issues) == 1
        assert issues[0].suggestion is not None
        assert "public API" in issues[0].suggestion

"""Tests for observability rule.

Related ticket: OMN-1906
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleObservabilityConfig,
)
from omnibase_core.validation.cross_repo.rules.rule_observability import (
    RuleObservability,
)
from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
)


@pytest.mark.unit
class TestRuleObservability:
    """Tests for RuleObservability."""

    @pytest.fixture
    def config(self) -> ModelRuleObservabilityConfig:
        """Create a test configuration."""
        return ModelRuleObservabilityConfig(
            enabled=True,
            exclude_patterns=["tests/**", "scripts/**", "migrations/**", "examples/**"],
            flag_print=True,
            flag_raw_logging=True,
            print_severity=EnumSeverity.ERROR,
            raw_logging_severity=EnumSeverity.WARNING,
        )

    @pytest.fixture
    def tmp_src_dir(self, tmp_path: Path) -> Path:
        """Create a temporary src directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        return src_dir

    def test_detects_print_call(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that print() calls are detected."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
def process_data(data):
    print("Processing:", data)
    return data
"""
        )

        rule = RuleObservability(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].code == "OBSERVABILITY_PRINT"
        assert issues[0].severity == EnumSeverity.ERROR

    def test_detects_logging_get_logger(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that logging.getLogger() calls are detected."""
        source_file = tmp_src_dir / "service.py"
        source_file.write_text(
            """\
import logging

logger = logging.getLogger(__name__)

def do_work():
    logger.info("Working...")
"""
        )

        rule = RuleObservability(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].code == "OBSERVABILITY_RAW_LOGGING"
        assert issues[0].severity == EnumSeverity.WARNING

    def test_detects_log_alias_get_logger(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that log.getLogger() (alias) calls are detected."""
        source_file = tmp_src_dir / "service.py"
        source_file.write_text(
            """\
import logging as log

logger = log.getLogger(__name__)
"""
        )

        rule = RuleObservability(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].code == "OBSERVABILITY_RAW_LOGGING"

    def test_no_issues_for_clean_code(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that clean code passes."""
        source_file = tmp_src_dir / "clean.py"
        source_file.write_text(
            """\
def process_data(data):
    # Uses structured logging via dependency injection
    return data * 2
"""
        )

        rule = RuleObservability(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_excludes_test_files(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
    ) -> None:
        """Test that test files are excluded."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_handler.py"
        test_file.write_text(
            """\
def test_something():
    print("Debug output")  # OK in tests
"""
        )

        rule = RuleObservability(config)
        file_imports = {
            test_file: ModelFileImports(file_path=test_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_excludes_scripts_files(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
    ) -> None:
        """Test that script files are excluded."""
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        script_file = scripts_dir / "deploy.py"
        script_file.write_text(
            """\
import logging
logger = logging.getLogger(__name__)
print("Deploying...")
"""
        )

        rule = RuleObservability(config)
        file_imports = {
            script_file: ModelFileImports(file_path=script_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_excludes_migrations_files(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
    ) -> None:
        """Test that migration files are excluded."""
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        migration_file = migrations_dir / "001_initial.py"
        migration_file.write_text(
            """\
def upgrade():
    print("Migrating...")
"""
        )

        rule = RuleObservability(config)
        file_imports = {
            migration_file: ModelFileImports(file_path=migration_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_excludes_allowlist_modules(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that allowlisted modules are excluded."""
        config = ModelRuleObservabilityConfig(
            enabled=True,
            flag_print=True,
            flag_raw_logging=True,
            allowlist_modules=["bootstrap", "init"],
        )

        bootstrap_dir = tmp_src_dir / "bootstrap"
        bootstrap_dir.mkdir()

        bootstrap_file = bootstrap_dir / "early_init.py"
        bootstrap_file.write_text(
            """\
import logging
logger = logging.getLogger(__name__)
print("Bootstrapping...")
"""
        )

        rule = RuleObservability(config)
        file_imports = {
            bootstrap_file: ModelFileImports(file_path=bootstrap_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_disabled_rule_returns_no_issues(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that disabled rules don't report issues."""
        disabled_config = ModelRuleObservabilityConfig(enabled=False)

        source_file = tmp_src_dir / "handler.py"
        source_file.write_text('print("Hello")')

        rule = RuleObservability(disabled_config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_flag_print_false(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that flag_print=False skips print detection."""
        config = ModelRuleObservabilityConfig(
            enabled=True,
            flag_print=False,
            flag_raw_logging=True,
        )

        source_file = tmp_src_dir / "handler.py"
        source_file.write_text('print("Hello")')

        rule = RuleObservability(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_flag_raw_logging_false(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that flag_raw_logging=False skips logging detection."""
        config = ModelRuleObservabilityConfig(
            enabled=True,
            flag_print=True,
            flag_raw_logging=False,
        )

        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import logging
logger = logging.getLogger(__name__)
"""
        )

        rule = RuleObservability(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_issue_contains_fingerprint_and_symbol(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that issues include fingerprint and symbol for baseline tracking."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text('print("Debug")')

        rule = RuleObservability(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].context is not None
        assert issues[0].context.get("symbol") == "print"
        fingerprint = issues[0].context.get("fingerprint")
        assert fingerprint is not None
        assert len(fingerprint) == 16
        assert all(c in "0123456789abcdef" for c in fingerprint)

    def test_issue_has_suggestion(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that issues include suggestions."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text('print("Debug")')

        rule = RuleObservability(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].suggestion is not None
        assert "ProtocolLogger" in issues[0].suggestion

    def test_multiple_violations_in_file(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test detection of multiple violations in one file."""
        source_file = tmp_src_dir / "bad_code.py"
        source_file.write_text(
            """\
import logging

logger = logging.getLogger(__name__)

def process():
    print("Starting")
    print("Done")
"""
        )

        rule = RuleObservability(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # 1 logging.getLogger + 2 prints = 3 issues
        assert len(issues) == 3
        codes = [i.code for i in issues]
        assert codes.count("OBSERVABILITY_PRINT") == 2
        assert codes.count("OBSERVABILITY_RAW_LOGGING") == 1

    def test_handles_syntax_errors(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that syntax errors are handled gracefully."""
        source_file = tmp_src_dir / "bad.py"
        source_file.write_text("print( syntax error")

        rule = RuleObservability(config)
        file_imports = {
            source_file: ModelFileImports(
                file_path=source_file, parse_error="Syntax error"
            ),
        }

        # Should not raise
        issues = rule.validate(file_imports, "test_repo", tmp_path)
        assert len(issues) == 0

    def test_handles_missing_files(
        self,
        config: ModelRuleObservabilityConfig,
        tmp_path: Path,
    ) -> None:
        """Test that missing files are handled gracefully."""
        missing_file = tmp_path / "nonexistent.py"

        rule = RuleObservability(config)
        file_imports = {
            missing_file: ModelFileImports(file_path=missing_file),
        }

        # Should not raise
        issues = rule.validate(file_imports, "test_repo", tmp_path)
        assert len(issues) == 0

    def test_allowlist_no_substring_match(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that allowlist uses segment matching, not substring matching.

        Regression test for PR #488: "cli" should match "cli/commands.py"
        but NOT "public_client.py" where "cli" is a substring of "client".
        """
        config = ModelRuleObservabilityConfig(
            enabled=True,
            flag_print=True,
            flag_raw_logging=True,
            allowlist_modules=["cli"],
        )

        # This file SHOULD be excluded (cli is a directory segment)
        cli_dir = tmp_src_dir / "cli"
        cli_dir.mkdir()
        cli_file = cli_dir / "commands.py"
        cli_file.write_text('print("CLI command")')

        # This file should NOT be excluded (cli is substring of client)
        client_file = tmp_src_dir / "public_client.py"
        client_file.write_text('print("Client code")')

        rule = RuleObservability(config)
        file_imports = {
            cli_file: ModelFileImports(file_path=cli_file),
            client_file: ModelFileImports(file_path=client_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Only client_file should have issues (cli_file is allowlisted)
        assert len(issues) == 1
        assert issues[0].file_path == client_file

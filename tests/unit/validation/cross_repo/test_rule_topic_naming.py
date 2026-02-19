# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for topic_naming rule.

Related ticket: OMN-1775
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleTopicNamingConfig,
)
from omnibase_core.validation.cross_repo.rules.rule_topic_naming import (
    RuleTopicNaming,
)
from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
)


class TestRuleTopicNaming:
    """Tests for RuleTopicNaming."""

    @pytest.fixture
    def config(self) -> ModelRuleTopicNamingConfig:
        """Create a test configuration."""
        return ModelRuleTopicNamingConfig(
            enabled=True,
            severity=EnumSeverity.ERROR,
            require_env_prefix=False,
            allowed_patterns=[
                r"^onex\.(cmd|evt|dlq|intent|snapshot)\.[a-z0-9-]+\.[a-z0-9-]+\.v[0-9]+$",
            ],
            constants_module="omnibase_core.constants.constants_topic_taxonomy",
        )

    @pytest.fixture
    def tmp_src_dir(self, tmp_path: Path) -> Path:
        """Create a temporary source directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        return src_dir

    def test_detects_invalid_topic_format(
        self,
        config: ModelRuleTopicNamingConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that invalid topic formats are detected."""
        py_file = tmp_src_dir / "bad_topics.py"
        py_file.write_text(
            """
TOPIC = "onex.invalid.format"  # Missing segments
"""
        )

        rule = RuleTopicNaming(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Should detect invalid format
        invalid_issues = [i for i in issues if i.code == "TOPIC_NAMING_INVALID_FORMAT"]
        assert len(invalid_issues) == 1
        assert "onex.invalid.format" in invalid_issues[0].message

    def test_detects_hardcoded_topic(
        self,
        config: ModelRuleTopicNamingConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that hardcoded topics outside constants module are flagged."""
        py_file = tmp_src_dir / "hardcoded_topics.py"
        py_file.write_text(
            """
# Hardcoded topic - should be in constants
TOPIC = "onex.evt.service.event-name.v1"
"""
        )

        rule = RuleTopicNaming(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Should detect hardcoded topic (warning)
        hardcoded_issues = [i for i in issues if i.code == "TOPIC_NAMING_HARDCODED"]
        assert len(hardcoded_issues) == 1
        assert hardcoded_issues[0].severity == EnumSeverity.WARNING

    def test_skips_constants_module(
        self,
        config: ModelRuleTopicNamingConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that the constants module is not flagged for hardcoded topics."""
        # Create a file with the constants module name
        constants_file = tmp_src_dir / "constants_topic_taxonomy.py"
        constants_file.write_text(
            """
# This is the constants module - topics should be defined here
TOPIC_CONTRACT_REGISTERED = "onex.evt.contract-registered.v1"
TOPIC_HEARTBEAT = "onex.evt.node-heartbeat.v1"
"""
        )

        rule = RuleTopicNaming(config)
        file_imports = {
            constants_file: ModelFileImports(file_path=constants_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Should not flag topics in constants module
        assert len(issues) == 0

    def test_skips_non_topic_strings(
        self,
        config: ModelRuleTopicNamingConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that non-topic strings are ignored."""
        py_file = tmp_src_dir / "normal_code.py"
        py_file.write_text(
            """
message = "Hello world"
url = "https://example.com/api"
path = "/usr/local/bin"
"""
        )

        rule = RuleTopicNaming(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_skips_when_disabled(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that rule is skipped when disabled."""
        config = ModelRuleTopicNamingConfig(enabled=False)

        py_file = tmp_src_dir / "bad_topics.py"
        py_file.write_text(
            """
TOPIC = "onex.invalid.format"
"""
        )

        rule = RuleTopicNaming(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_detects_forbidden_pattern(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that forbidden patterns are detected."""
        config = ModelRuleTopicNamingConfig(
            enabled=True,
            forbidden_patterns=[r".*\.legacy\..*"],
        )

        py_file = tmp_src_dir / "legacy_topics.py"
        py_file.write_text(
            """
TOPIC = "onex.legacy.old-service.v1"
"""
        )

        rule = RuleTopicNaming(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        forbidden_issues = [
            i for i in issues if i.code == "TOPIC_NAMING_FORBIDDEN_PATTERN"
        ]
        assert len(forbidden_issues) == 1

    def test_handles_syntax_errors(
        self,
        config: ModelRuleTopicNamingConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that files with syntax errors are skipped gracefully."""
        py_file = tmp_src_dir / "syntax_error.py"
        py_file.write_text(
            """
def broken(
    # Missing closing paren
"""
        )

        rule = RuleTopicNaming(config)
        file_imports = {
            py_file: ModelFileImports(file_path=py_file, imports=()),
        }

        # Should not raise, should return empty
        issues = rule.validate(file_imports, "test_repo", tmp_path)
        assert len(issues) == 0

"""Tests for partition_key rule.

Related ticket: OMN-1906
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.validation.model_rule_configs import (
    ModelRulePartitionKeyConfig,
)
from omnibase_core.validation.cross_repo.rules.rule_partition_key import (
    RulePartitionKey,
)
from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
)


class TestRulePartitionKey:
    """Tests for RulePartitionKey."""

    @pytest.fixture
    def config(self) -> ModelRulePartitionKeyConfig:
        """Create a test configuration."""
        return ModelRulePartitionKeyConfig(
            enabled=True,
            severity=EnumSeverity.ERROR,
            require_partition_key=True,
            allowed_strategies=["correlation_id", "entity_id", "tenant_id", "none"],
            topic_config_pattern=r"Model.*Topic.*Config",
        )

    @pytest.fixture
    def tmp_src_dir(self, tmp_path: Path) -> Path:
        """Create a temporary src directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        return src_dir

    def test_detects_missing_partition_key(
        self,
        config: ModelRulePartitionKeyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that missing partition_key is detected."""
        topic_config = tmp_src_dir / "topic_config.py"
        topic_config.write_text(
            """\
from pydantic import BaseModel

class ModelEventTopicConfig(BaseModel):
    topic_name: str
    # Missing partition_key!
"""
        )

        rule = RulePartitionKey(config)
        file_imports = {
            topic_config: ModelFileImports(file_path=topic_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].code == "MISSING_PARTITION_KEY"
        assert "ModelEventTopicConfig" in issues[0].message

    def test_no_issues_with_partition_key_annotation(
        self,
        config: ModelRulePartitionKeyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that annotated partition_key passes."""
        topic_config = tmp_src_dir / "topic_config.py"
        topic_config.write_text(
            """\
from pydantic import BaseModel

class ModelEventTopicConfig(BaseModel):
    topic_name: str
    partition_key: str = "correlation_id"
"""
        )

        rule = RulePartitionKey(config)
        file_imports = {
            topic_config: ModelFileImports(file_path=topic_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_no_issues_with_partition_key_field(
        self,
        config: ModelRulePartitionKeyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that Field() partition_key passes."""
        topic_config = tmp_src_dir / "topic_config.py"
        topic_config.write_text(
            """\
from pydantic import BaseModel, Field

class ModelEventTopicConfig(BaseModel):
    topic_name: str
    partition_key: str = Field(default="entity_id")
"""
        )

        rule = RulePartitionKey(config)
        file_imports = {
            topic_config: ModelFileImports(file_path=topic_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_no_issues_with_simple_assignment(
        self,
        config: ModelRulePartitionKeyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that simple assignment partition_key passes."""
        topic_config = tmp_src_dir / "topic_config.py"
        topic_config.write_text(
            """\
class ModelCommandTopicConfig:
    partition_key = "tenant_id"
    topic_name = "commands"
"""
        )

        rule = RulePartitionKey(config)
        file_imports = {
            topic_config: ModelFileImports(file_path=topic_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_ignores_non_topic_config_classes(
        self,
        config: ModelRulePartitionKeyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that non-topic config classes are ignored."""
        other_config = tmp_src_dir / "other_config.py"
        other_config.write_text(
            """\
from pydantic import BaseModel

class ModelDatabaseConfig(BaseModel):
    host: str
    port: int
    # No partition_key needed - not a topic config
"""
        )

        rule = RulePartitionKey(config)
        file_imports = {
            other_config: ModelFileImports(file_path=other_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_disabled_rule_returns_no_issues(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that disabled rules don't report issues."""
        disabled_config = ModelRulePartitionKeyConfig(enabled=False)

        topic_config = tmp_src_dir / "topic_config.py"
        topic_config.write_text(
            """\
class ModelEventTopicConfig:
    topic_name = "events"
    # Missing partition_key but rule is disabled
"""
        )

        rule = RulePartitionKey(disabled_config)
        file_imports = {
            topic_config: ModelFileImports(file_path=topic_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_require_partition_key_false(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that require_partition_key=False skips validation."""
        config = ModelRulePartitionKeyConfig(
            enabled=True,
            require_partition_key=False,
        )

        topic_config = tmp_src_dir / "topic_config.py"
        topic_config.write_text(
            """\
class ModelEventTopicConfig:
    topic_name = "events"
"""
        )

        rule = RulePartitionKey(config)
        file_imports = {
            topic_config: ModelFileImports(file_path=topic_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_custom_topic_pattern(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test custom topic config pattern."""
        custom_config = ModelRulePartitionKeyConfig(
            enabled=True,
            severity=EnumSeverity.ERROR,
            require_partition_key=True,
            topic_config_pattern=r".*KafkaConfig$",
        )

        topic_config = tmp_src_dir / "kafka_config.py"
        topic_config.write_text(
            """\
class EventsKafkaConfig:
    topic_name = "events"
    # Missing partition_key
"""
        )

        rule = RulePartitionKey(custom_config)
        file_imports = {
            topic_config: ModelFileImports(file_path=topic_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert "EventsKafkaConfig" in issues[0].message

    def test_issue_contains_fingerprint_and_symbol(
        self,
        config: ModelRulePartitionKeyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that issues include fingerprint and symbol for baseline tracking."""
        topic_config = tmp_src_dir / "topic_config.py"
        topic_config.write_text(
            """\
class ModelEventTopicConfig:
    topic_name = "events"
"""
        )

        rule = RulePartitionKey(config)
        file_imports = {
            topic_config: ModelFileImports(file_path=topic_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].context is not None
        assert issues[0].context.get("symbol") == "ModelEventTopicConfig"
        fingerprint = issues[0].context.get("fingerprint")
        assert fingerprint is not None
        assert len(fingerprint) == 16
        assert all(c in "0123456789abcdef" for c in fingerprint)

    def test_issue_has_suggestion(
        self,
        config: ModelRulePartitionKeyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that issues include suggestions with allowed strategies."""
        topic_config = tmp_src_dir / "topic_config.py"
        topic_config.write_text(
            """\
class ModelEventTopicConfig:
    topic_name = "events"
"""
        )

        rule = RulePartitionKey(config)
        file_imports = {
            topic_config: ModelFileImports(file_path=topic_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].suggestion is not None
        assert "partition_key" in issues[0].suggestion
        assert "correlation_id" in issues[0].suggestion

    def test_multiple_topic_configs_in_file(
        self,
        config: ModelRulePartitionKeyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test detection of multiple topic configs in one file."""
        topic_config = tmp_src_dir / "topic_configs.py"
        topic_config.write_text(
            """\
from pydantic import BaseModel

class ModelEventTopicConfig(BaseModel):
    topic_name: str
    # Missing partition_key

class ModelCommandTopicConfig(BaseModel):
    topic_name: str
    partition_key: str = "entity_id"  # Has partition_key

class ModelResponseTopicConfig(BaseModel):
    topic_name: str
    # Also missing partition_key
"""
        )

        rule = RulePartitionKey(config)
        file_imports = {
            topic_config: ModelFileImports(file_path=topic_config),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        class_names = [i.context["class_name"] for i in issues if i.context]
        assert "ModelEventTopicConfig" in class_names
        assert "ModelResponseTopicConfig" in class_names
        assert "ModelCommandTopicConfig" not in class_names

    def test_handles_syntax_errors(
        self,
        config: ModelRulePartitionKeyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that syntax errors are handled gracefully."""
        topic_config = tmp_src_dir / "bad_topic.py"
        topic_config.write_text("class ModelEventTopicConfig syntax error")

        rule = RulePartitionKey(config)
        file_imports = {
            topic_config: ModelFileImports(
                file_path=topic_config, parse_error="Syntax error"
            ),
        }

        # Should not raise
        issues = rule.validate(file_imports, "test_repo", tmp_path)
        assert len(issues) == 0

    def test_handles_missing_files(
        self,
        config: ModelRulePartitionKeyConfig,
        tmp_path: Path,
    ) -> None:
        """Test that missing files are handled gracefully."""
        missing_file = tmp_path / "nonexistent.py"

        rule = RulePartitionKey(config)
        file_imports = {
            missing_file: ModelFileImports(file_path=missing_file),
        }

        # Should not raise
        issues = rule.validate(file_imports, "test_repo", tmp_path)
        assert len(issues) == 0

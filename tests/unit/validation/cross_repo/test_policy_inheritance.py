# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for policy inheritance in cross-repo validation.

Tests the shallow inheritance feature where child policies can extend
a single parent policy. Multi-level inheritance is explicitly forbidden.

Related ticket: OMN-1774
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleRepoBoundariesConfig,
)
from omnibase_core.validation.cross_repo.policy_loader import load_policy

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "cross_repo_validation"
)


class TestPolicyInheritance:
    """Tests for policy inheritance via the extends field."""

    def test_child_overrides_parent_scalars(self) -> None:
        """Test that child scalar values override parent values."""
        policy_path = FIXTURES_DIR / "policies" / "child_policy.yaml"
        policy = load_policy(policy_path)

        # Child should override policy_id
        assert policy.policy_id == "my_app_policy"

        # Child should override repo_id
        assert policy.repo_id == "my_app"

        # Child should override policy_version
        assert policy.policy_version.major == 2
        assert policy.policy_version.minor == 1
        assert policy.policy_version.patch == 0

    def test_dict_merging_child_wins_on_conflict(self) -> None:
        """Test that dict fields merge with child winning on conflict."""
        policy_path = FIXTURES_DIR / "policies" / "child_policy.yaml"
        policy = load_policy(policy_path)

        repo_boundaries = policy.rules.get("repo_boundaries")
        assert repo_boundaries is not None
        assert isinstance(repo_boundaries, ModelRuleRepoBoundariesConfig)

        # Ownership should be merged: parent's base_module + child's my_app
        assert "base_module." in repo_boundaries.ownership
        assert "my_app." in repo_boundaries.ownership
        assert repo_boundaries.ownership["base_module."] == "base_repo"
        assert repo_boundaries.ownership["my_app."] == "my_app"

    def test_list_concatenation(self) -> None:
        """Test that list fields concatenate (parent first, then child)."""
        policy_path = FIXTURES_DIR / "policies" / "child_policy.yaml"
        policy = load_policy(policy_path)

        repo_boundaries = policy.rules.get("repo_boundaries")
        assert repo_boundaries is not None
        assert isinstance(repo_boundaries, ModelRuleRepoBoundariesConfig)

        # forbidden_import_prefixes should be concatenated
        # Parent has: ["internal.private"]
        # Child has: ["internal_module"]
        # Result should have both (parent first, then child)
        assert "internal.private" in repo_boundaries.forbidden_import_prefixes
        assert "internal_module" in repo_boundaries.forbidden_import_prefixes

    def test_parent_values_preserved_when_child_omits(self) -> None:
        """Test that parent values are preserved when child doesn't override."""
        policy_path = FIXTURES_DIR / "policies" / "child_policy.yaml"
        policy = load_policy(policy_path)

        repo_boundaries = policy.rules.get("repo_boundaries")
        assert repo_boundaries is not None
        assert isinstance(repo_boundaries, ModelRuleRepoBoundariesConfig)

        # enabled and severity should come from parent
        assert repo_boundaries.enabled is True

        # allowed_cross_repo_prefixes should come from parent
        # (child didn't specify this field)
        assert "shared.protocols" in repo_boundaries.allowed_cross_repo_prefixes

    def test_error_on_multi_level_inheritance(self) -> None:
        """Test that multi-level inheritance raises a clear error."""
        policy_path = FIXTURES_DIR / "policies" / "grandchild_policy.yaml"

        with pytest.raises(ModelOnexError) as exc_info:
            load_policy(policy_path)

        error = exc_info.value
        assert "multi-level" in error.message.lower()
        assert "not supported" in error.message.lower()
        assert error.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR

    def test_missing_parent_file_error(self, tmp_path: Path) -> None:
        """Test error when parent policy file doesn't exist."""
        child_yaml = tmp_path / "child.yaml"
        child_yaml.write_text(
            """
extends: ./nonexistent_parent.yaml
policy_id: orphan_child
repo_id: orphan
rules: {}
"""
        )

        with pytest.raises(ModelOnexError) as exc_info:
            load_policy(child_yaml)

        error = exc_info.value
        assert "not found" in error.message.lower()
        assert "nonexistent_parent.yaml" in error.message
        assert error.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_base_policy_loads_without_extends(self) -> None:
        """Test that base policy (without extends) loads correctly."""
        policy_path = FIXTURES_DIR / "policies" / "base_policy.yaml"
        policy = load_policy(policy_path)

        assert policy.policy_id == "onex_base_defaults"
        assert policy.repo_id == "_base"
        assert policy.extends is None

        # Verify rules are present
        repo_boundaries = policy.rules.get("repo_boundaries")
        assert repo_boundaries is not None
        assert repo_boundaries.enabled is True

    def test_extends_not_propagated_to_merged_policy(self) -> None:
        """Test that the extends field is not in the final merged policy."""
        policy_path = FIXTURES_DIR / "policies" / "child_policy.yaml"
        policy = load_policy(policy_path)

        # The extends field should be None in the final result
        # (it's a directive that was used during loading, not data)
        assert policy.extends is None

    def test_discovery_config_merges(self) -> None:
        """Test that discovery config fields merge correctly."""
        policy_path = FIXTURES_DIR / "policies" / "child_policy.yaml"
        policy = load_policy(policy_path)

        # include_globs should be concatenated
        # Parent has: ["**/*.py"]
        # Child has: ["src/**/*.py"]
        assert "**/*.py" in policy.discovery.include_globs
        assert "src/**/*.py" in policy.discovery.include_globs

        # exclude_globs should come from parent (child didn't specify)
        assert "**/test_*.py" in policy.discovery.exclude_globs
        assert "**/__pycache__/**" in policy.discovery.exclude_globs


class TestPolicyInheritanceEdgeCases:
    """Edge case tests for policy inheritance."""

    def test_empty_child_inherits_all_parent(self, tmp_path: Path) -> None:
        """Test that an empty child inherits everything from parent."""
        # Create parent
        parent_yaml = tmp_path / "parent.yaml"
        parent_yaml.write_text(
            """
policy_id: full_parent
policy_version:
  major: 1
  minor: 0
  patch: 0
repo_id: parent_repo
discovery:
  include_globs: ["**/*.py"]
rules:
  repo_boundaries:
    enabled: true
    forbidden_import_prefixes:
      - "forbidden"
"""
        )

        # Create minimal child that just extends
        child_yaml = tmp_path / "child.yaml"
        child_yaml.write_text(
            """
extends: ./parent.yaml
policy_id: minimal_child
repo_id: child_repo
"""
        )

        policy = load_policy(child_yaml)

        # Child should override identity fields
        assert policy.policy_id == "minimal_child"
        assert policy.repo_id == "child_repo"

        # Everything else should come from parent
        assert "**/*.py" in policy.discovery.include_globs
        repo_boundaries = policy.rules.get("repo_boundaries")
        assert repo_boundaries is not None
        assert repo_boundaries.enabled is True
        assert "forbidden" in repo_boundaries.forbidden_import_prefixes

    def test_absolute_path_extends(self, tmp_path: Path) -> None:
        """Test that absolute paths work for extends field."""
        # Create parent in a different directory
        parent_dir = tmp_path / "base_policies"
        parent_dir.mkdir()
        parent_yaml = parent_dir / "org_defaults.yaml"
        parent_yaml.write_text(
            """
policy_id: org_defaults
policy_version:
  major: 1
  minor: 0
  patch: 0
repo_id: _org_base
discovery:
  include_globs: ["**/*.py"]
rules: {}
"""
        )

        # Create child with absolute path
        child_yaml = tmp_path / "child.yaml"
        child_yaml.write_text(
            f"""
extends: {parent_yaml}
policy_id: uses_absolute_path
repo_id: child_repo
rules: {{}}
"""
        )

        policy = load_policy(child_yaml)

        assert policy.policy_id == "uses_absolute_path"
        assert policy.repo_id == "child_repo"
        # Inherited from parent
        assert "**/*.py" in policy.discovery.include_globs

    def test_relative_path_parent_directory(self, tmp_path: Path) -> None:
        """Test that ../path style relative paths work."""
        # Create parent in parent directory
        parent_yaml = tmp_path / "org_base.yaml"
        parent_yaml.write_text(
            """
policy_id: org_base
policy_version:
  major: 1
  minor: 0
  patch: 0
repo_id: _org
discovery:
  include_globs: ["**/*.py"]
rules: {}
"""
        )

        # Create child in subdirectory
        child_dir = tmp_path / "repos" / "my_repo"
        child_dir.mkdir(parents=True)
        child_yaml = child_dir / "policy.yaml"
        child_yaml.write_text(
            """
extends: ../../org_base.yaml
policy_id: my_repo_policy
repo_id: my_repo
rules: {}
"""
        )

        policy = load_policy(child_yaml)

        assert policy.policy_id == "my_repo_policy"
        assert policy.repo_id == "my_repo"

    def test_invalid_parent_yaml_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid YAML in parent raises appropriate error."""
        # Create invalid parent
        parent_yaml = tmp_path / "bad_parent.yaml"
        parent_yaml.write_text("invalid: yaml: content: [")

        # Create child referencing invalid parent
        child_yaml = tmp_path / "child.yaml"
        child_yaml.write_text(
            """
extends: ./bad_parent.yaml
policy_id: child
repo_id: child
rules: {}
"""
        )

        with pytest.raises(ModelOnexError) as exc_info:
            load_policy(child_yaml)

        assert "parse" in exc_info.value.message.lower()
        assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR

    def test_child_can_override_discovery_completely(self, tmp_path: Path) -> None:
        """Test that child can fully replace discovery config."""
        # Create parent with discovery
        parent_yaml = tmp_path / "parent.yaml"
        parent_yaml.write_text(
            """
policy_id: parent
policy_version:
  major: 1
  minor: 0
  patch: 0
repo_id: parent
discovery:
  include_globs: ["old/**/*.py"]
  exclude_globs: ["old/tests/**"]
rules: {}
"""
        )

        # Create child that fully specifies discovery
        child_yaml = tmp_path / "child.yaml"
        child_yaml.write_text(
            """
extends: ./parent.yaml
policy_id: child
repo_id: child
discovery:
  include_globs: ["new/**/*.py"]
  exclude_globs: ["new/tests/**"]
rules: {}
"""
        )

        policy = load_policy(child_yaml)

        # Discovery lists should be concatenated (parent first, then child)
        assert "old/**/*.py" in policy.discovery.include_globs
        assert "new/**/*.py" in policy.discovery.include_globs
        assert "old/tests/**" in policy.discovery.exclude_globs
        assert "new/tests/**" in policy.discovery.exclude_globs

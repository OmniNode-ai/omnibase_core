# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for policy loader.

Related ticket: OMN-1771
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleRepoBoundariesConfig,
)
from omnibase_core.validation.cross_repo.policy_loader import load_policy

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "cross_repo_validation"
)


class TestLoadPolicy:
    """Tests for load_policy function."""

    def test_load_valid_policy(self) -> None:
        """Test loading a valid policy file."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        policy = load_policy(policy_path)

        assert policy.policy_id == "fake_app_validation"
        assert policy.repo_id == "fake_app"
        assert "repo_boundaries" in policy.rules

    def test_load_policy_file_not_found(self, tmp_path: Path) -> None:
        """Test error when policy file doesn't exist."""
        with pytest.raises(ModelOnexError) as exc_info:
            load_policy(tmp_path / "nonexistent.yaml")

        assert "not found" in str(exc_info.value.message).lower()

    def test_load_policy_invalid_yaml(self, tmp_path: Path) -> None:
        """Test error when YAML is invalid."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("invalid: yaml: content: [")

        with pytest.raises(ModelOnexError) as exc_info:
            load_policy(bad_yaml)

        assert "parse" in str(exc_info.value.message).lower()

    def test_policy_has_correct_rules(self) -> None:
        """Test that loaded policy has correct rule configs."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        policy = load_policy(policy_path)

        repo_boundaries = policy.rules.get("repo_boundaries")
        assert repo_boundaries is not None
        assert isinstance(repo_boundaries, ModelRuleRepoBoundariesConfig)
        assert repo_boundaries.enabled is True
        assert "fake_infra.services" in repo_boundaries.forbidden_import_prefixes

    def test_policy_version_parsed(self) -> None:
        """Test that policy version is parsed correctly."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        policy = load_policy(policy_path)

        assert policy.policy_version.major == 1
        assert policy.policy_version.minor == 0
        assert policy.policy_version.patch == 0

    def test_policy_discovery_config_parsed(self) -> None:
        """Test that discovery config is parsed correctly."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        policy = load_policy(policy_path)

        assert "**/*.py" in policy.discovery.include_globs
        assert "**/__pycache__/**" in policy.discovery.exclude_globs

    def test_load_minimal_policy(self, tmp_path: Path) -> None:
        """Test loading a minimal policy file."""
        minimal_yaml = tmp_path / "minimal.yaml"
        minimal_yaml.write_text(
            """
policy_id: minimal_test
repo_id: test_repo
rules: {}
"""
        )

        policy = load_policy(minimal_yaml)

        assert policy.policy_id == "minimal_test"
        assert policy.repo_id == "test_repo"
        assert len(policy.rules) == 0

    def test_load_fake_core_policy(self) -> None:
        """Test loading the fake_core policy."""
        policy_path = FIXTURES_DIR / "policies" / "fake_core_policy.yaml"
        policy = load_policy(policy_path)

        assert policy.policy_id == "fake_core_validation"
        assert policy.repo_id == "fake_core"

        repo_boundaries = policy.rules.get("repo_boundaries")
        assert repo_boundaries is not None
        assert isinstance(repo_boundaries, ModelRuleRepoBoundariesConfig)
        # fake_core has no forbidden prefixes
        assert len(repo_boundaries.forbidden_import_prefixes) == 0

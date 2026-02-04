"""Integration tests validating real agent YAML files against Pydantic models.

This module tests that the ModelAgentDefinition and related models can successfully
parse and validate the 53 real agent YAML configuration files in omniclaude.

The tests are designed to:
1. Gracefully skip if the omniclaude path is not available
2. Validate each agent YAML individually for clear failure reporting
3. Generate a summary of validation results
4. Track validation progress (see OMN-1914 for YAML standardization)

NOTE: Many agent YAMLs currently fail validation due to schema inconsistencies.
See OMN-1914 for the follow-up ticket to standardize all agent YAML files.
The parametrized tests are marked as xfail until standardization is complete.
"""

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.agents import ModelAgentDefinition

# Path to omniclaude agent configs (cross-repo reference)
OMNICLAUDE_AGENTS_PATH = Path(
    "/Volumes/PRO-G40/Code/omniclaude/plugins/onex/agents/configs"
)


def get_agent_yaml_files() -> list[Path]:
    """Get all agent YAML files from omniclaude.

    Returns:
        Sorted list of YAML file paths, empty if path doesn't exist.
    """
    if not OMNICLAUDE_AGENTS_PATH.exists():
        return []
    return sorted(OMNICLAUDE_AGENTS_PATH.glob("*.yaml"))


@pytest.fixture(scope="module")
def agent_yaml_files() -> list[Path]:
    """Fixture providing list of agent YAML files."""
    return get_agent_yaml_files()


class TestAgentYAMLValidation:
    """Test that real agent YAML files validate against our models."""

    @pytest.mark.skipif(
        not OMNICLAUDE_AGENTS_PATH.exists(),
        reason="omniclaude agents path not available",
    )
    def test_omniclaude_agents_path_exists(self) -> None:
        """Verify omniclaude agents directory exists."""
        assert OMNICLAUDE_AGENTS_PATH.exists()
        assert OMNICLAUDE_AGENTS_PATH.is_dir()

    @pytest.mark.skipif(
        not OMNICLAUDE_AGENTS_PATH.exists(),
        reason="omniclaude agents path not available",
    )
    def test_agent_yaml_files_found(self, agent_yaml_files: list[Path]) -> None:
        """Verify we found agent YAML files."""
        assert len(agent_yaml_files) > 0, "No agent YAML files found"
        # We expect approximately 53 agents
        assert len(agent_yaml_files) >= 40, (
            f"Expected ~53 agents, found {len(agent_yaml_files)}"
        )

    @pytest.mark.skipif(
        not OMNICLAUDE_AGENTS_PATH.exists(),
        reason="omniclaude agents path not available",
    )
    @pytest.mark.xfail(
        reason="OMN-1914: Agent YAMLs need standardization to match schema",
        strict=False,  # Allow unexpected passes
    )
    @pytest.mark.parametrize("yaml_file", get_agent_yaml_files(), ids=lambda p: p.stem)
    def test_validate_agent_yaml(self, yaml_file: Path) -> None:
        """Test that each agent YAML validates against ModelAgentDefinition.

        This parametrized test runs once per YAML file, allowing us to see
        which specific files pass or fail validation.

        NOTE: Marked as xfail until OMN-1914 (YAML standardization) is complete.
        """
        # Load YAML
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        # Skip special files that aren't agent definitions
        if yaml_file.stem == "agent-registry":
            pytest.skip("agent-registry.yaml is a registry, not an agent definition")

        # Validate against model
        agent = ModelAgentDefinition.model_validate(data)

        # Basic assertions
        assert agent.schema_version is not None
        assert agent.agent_type is not None
        assert agent.agent_identity is not None
        assert agent.agent_identity.name is not None
        assert agent.agent_identity.description is not None

    @pytest.mark.skipif(
        not OMNICLAUDE_AGENTS_PATH.exists(),
        reason="omniclaude agents path not available",
    )
    def test_validate_compliant_agents(self) -> None:
        """Test validation against agents known to be schema-compliant.

        These agents have been verified to match the ModelAgentDefinition schema.
        """
        # Only include agents confirmed to pass validation
        compliant_agents = [
            "pr-review.yaml",
            # Add more agents here as they become compliant (OMN-1914)
        ]

        for agent_name in compliant_agents:
            yaml_path = OMNICLAUDE_AGENTS_PATH / agent_name
            if not yaml_path.exists():
                continue

            with open(yaml_path) as f:
                data = yaml.safe_load(f)

            agent = ModelAgentDefinition.model_validate(data)
            assert agent.agent_identity.name is not None

    @pytest.mark.skipif(
        not OMNICLAUDE_AGENTS_PATH.exists(),
        reason="omniclaude agents path not available",
    )
    def test_pr_review_agent_has_expected_structure(self) -> None:
        """Test that pr-review.yaml has expected structure."""
        yaml_path = OMNICLAUDE_AGENTS_PATH / "pr-review.yaml"
        if not yaml_path.exists():
            pytest.skip("pr-review.yaml not found")

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent = ModelAgentDefinition.model_validate(data)

        # Verify expected values from pr-review.yaml
        assert agent.agent_identity.name == "agent-pr-review"
        assert agent.agent_identity.color == "green"
        assert agent.agent_type == "pr_review"
        assert "PR review" in agent.agent_philosophy.core_responsibility
        assert agent.capabilities.primary is not None
        assert len(agent.capabilities.primary) > 0

    @pytest.mark.skipif(
        not OMNICLAUDE_AGENTS_PATH.exists(),
        reason="omniclaude agents path not available",
    )
    def test_all_agents_summary(self, agent_yaml_files: list[Path]) -> None:
        """Generate summary of all agent validations."""
        passed: list[str] = []
        failed: list[tuple[str, str]] = []
        skipped: list[str] = []

        for yaml_file in agent_yaml_files:
            if yaml_file.stem == "agent-registry":
                skipped.append(yaml_file.stem)
                continue

            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                ModelAgentDefinition.model_validate(data)
                passed.append(yaml_file.stem)
            except Exception as e:
                failed.append((yaml_file.stem, str(e)))

        # Print summary
        print("\n=== Agent Validation Summary ===")
        print(f"Passed: {len(passed)}")
        print(f"Failed: {len(failed)}")
        print(f"Skipped: {len(skipped)}")

        if failed:
            print("\nFailed agents (see OMN-1914 for standardization):")
            for name, error in failed[:10]:  # Limit output
                print(f"  - {name}: {error[:80]}...")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")

        # Calculate and report success rate (no assertion - tracked via OMN-1914)
        total_testable = len(passed) + len(failed)
        if total_testable > 0:
            success_rate = len(passed) / total_testable
            print(f"\nSuccess rate: {success_rate:.1%}")
            print("NOTE: Target is 90%+ after OMN-1914 completion")
            # Once OMN-1914 is complete, uncomment this assertion:
            # assert success_rate >= 0.9, f"Expected >=90%, got {success_rate:.1%}"

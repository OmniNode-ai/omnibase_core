# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumAgentCapability.

Tests all aspects of the agent capability enum including:
- Enum value validation
- Capability classification (code-related, requires large model)
- String representation
- JSON serialization compatibility
- Pydantic integration
- Instance methods (is_code_related, requires_large_model)
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability


@pytest.mark.unit
class TestEnumAgentCapability:
    """Test basic enum functionality."""

    def test_enum_values_code_related(self):
        """Test that all code-related capability enum values are present."""
        code_capabilities = {
            "CODE_GENERATION": "code_generation",
            "CODE_REVIEW": "code_review",
            "CODE_REFACTORING": "code_refactoring",
            "CODE_ANALYSIS": "code_analysis",
            "CODE_COMPLETION": "code_completion",
        }

        for name, value in code_capabilities.items():
            capability = getattr(EnumAgentCapability, name)
            assert capability.value == value

    def test_enum_values_reasoning(self):
        """Test that all reasoning capability enum values are present."""
        reasoning_capabilities = {
            "REASONING": "reasoning",
            "COMPLEX_ANALYSIS": "complex_analysis",
            "QUICK_VALIDATION": "quick_validation",
            "ROOT_CAUSE_ANALYSIS": "root_cause_analysis",
        }

        for name, value in reasoning_capabilities.items():
            capability = getattr(EnumAgentCapability, name)
            assert capability.value == value

    def test_enum_values_documentation(self):
        """Test that all documentation capability enum values are present."""
        doc_capabilities = {
            "DOCUMENTATION": "documentation",
            "TECHNICAL_WRITING": "technical_writing",
            "EXPLANATION": "explanation",
            "TUTORIAL_GENERATION": "tutorial_generation",
        }

        for name, value in doc_capabilities.items():
            capability = getattr(EnumAgentCapability, name)
            assert capability.value == value

    def test_enum_values_general(self):
        """Test that all general capability enum values are present."""
        general_capabilities = {
            "GENERAL_TASKS": "general_tasks",
            "ARCHITECTURE_DESIGN": "architecture_design",
            "SECURITY_ANALYSIS": "security_analysis",
            "PERFORMANCE_OPTIMIZATION": "performance_optimization",
        }

        for name, value in general_capabilities.items():
            capability = getattr(EnumAgentCapability, name)
            assert capability.value == value

    def test_enum_values_special(self):
        """Test that all special capability enum values are present."""
        special_capabilities = {
            "MULTIMODAL": "multimodal",
            "EMBEDDINGS": "embeddings",
            "LONG_CONTEXT": "long_context",
            "FAST_INFERENCE": "fast_inference",
        }

        for name, value in special_capabilities.items():
            capability = getattr(EnumAgentCapability, name)
            assert capability.value == value

    def test_enum_values_language(self):
        """Test that language capability enum value is present."""
        assert EnumAgentCapability.MULTILINGUAL.value == "multilingual"

    def test_string_representation(self):
        """Test string representation of enum values."""
        # Note: EnumAgentCapability doesn't override __str__, so it uses default
        assert EnumAgentCapability.CODE_GENERATION.value == "code_generation"
        assert EnumAgentCapability.REASONING.value == "reasoning"
        assert EnumAgentCapability.DOCUMENTATION.value == "documentation"


@pytest.mark.unit
class TestEnumAgentCapabilityInstanceMethods:
    """Test instance methods on enum values."""

    def test_is_code_related_true_cases(self):
        """Test is_code_related returns True for code-related capabilities."""
        code_capabilities = [
            EnumAgentCapability.CODE_GENERATION,
            EnumAgentCapability.CODE_REVIEW,
            EnumAgentCapability.CODE_REFACTORING,
            EnumAgentCapability.CODE_ANALYSIS,
            EnumAgentCapability.CODE_COMPLETION,
        ]

        for capability in code_capabilities:
            assert capability.is_code_related() is True, (
                f"{capability} should be code-related"
            )

    def test_is_code_related_false_cases(self):
        """Test is_code_related returns False for non-code capabilities."""
        non_code_capabilities = [
            EnumAgentCapability.REASONING,
            EnumAgentCapability.DOCUMENTATION,
            EnumAgentCapability.GENERAL_TASKS,
            EnumAgentCapability.MULTIMODAL,
            EnumAgentCapability.MULTILINGUAL,
        ]

        for capability in non_code_capabilities:
            assert capability.is_code_related() is False, (
                f"{capability} should not be code-related"
            )

    def test_is_code_related_prefix_matching(self):
        """Test that is_code_related uses prefix matching (starts with 'code_')."""
        # All code_ prefixed capabilities should return True
        all_capabilities = list(EnumAgentCapability)
        code_prefixed = [c for c in all_capabilities if c.value.startswith("code_")]

        for capability in code_prefixed:
            assert capability.is_code_related() is True

    def test_requires_large_model_true_cases(self):
        """Test requires_large_model returns True for appropriate capabilities."""
        large_model_capabilities = [
            EnumAgentCapability.COMPLEX_ANALYSIS,
            EnumAgentCapability.ARCHITECTURE_DESIGN,
            EnumAgentCapability.LONG_CONTEXT,
            EnumAgentCapability.REASONING,
        ]

        for capability in large_model_capabilities:
            assert capability.requires_large_model() is True, (
                f"{capability} should require large model"
            )

    def test_requires_large_model_false_cases(self):
        """Test requires_large_model returns False for capabilities that don't need it."""
        small_model_capabilities = [
            EnumAgentCapability.CODE_COMPLETION,
            EnumAgentCapability.QUICK_VALIDATION,
            EnumAgentCapability.FAST_INFERENCE,
            EnumAgentCapability.GENERAL_TASKS,
        ]

        for capability in small_model_capabilities:
            assert capability.requires_large_model() is False, (
                f"{capability} should not require large model"
            )

    def test_combined_method_logic(self):
        """Test combined logic of is_code_related and requires_large_model."""
        # CODE_GENERATION: code-related but doesn't require large model
        assert EnumAgentCapability.CODE_GENERATION.is_code_related() is True
        assert EnumAgentCapability.CODE_GENERATION.requires_large_model() is False

        # COMPLEX_ANALYSIS: not code-related but requires large model
        assert EnumAgentCapability.COMPLEX_ANALYSIS.is_code_related() is False
        assert EnumAgentCapability.COMPLEX_ANALYSIS.requires_large_model() is True

        # FAST_INFERENCE: neither code-related nor requires large model
        assert EnumAgentCapability.FAST_INFERENCE.is_code_related() is False
        assert EnumAgentCapability.FAST_INFERENCE.requires_large_model() is False


@pytest.mark.unit
class TestEnumAgentCapabilityIntegration:
    """Test integration with other systems."""

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert (
            EnumAgentCapability.CODE_GENERATION == EnumAgentCapability.CODE_GENERATION
        )
        assert EnumAgentCapability.REASONING != EnumAgentCapability.DOCUMENTATION
        assert EnumAgentCapability.MULTIMODAL == EnumAgentCapability.MULTIMODAL

    def test_enum_membership(self):
        """Test enum membership checking."""
        assert EnumAgentCapability.CODE_GENERATION in EnumAgentCapability
        assert EnumAgentCapability.REASONING in EnumAgentCapability
        assert EnumAgentCapability.MULTIMODAL in EnumAgentCapability

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        capabilities = list(EnumAgentCapability)
        # Should have 22 capabilities total
        assert len(capabilities) == 22

        # Verify key capabilities are present
        capability_values = [c.value for c in capabilities]
        assert "code_generation" in capability_values
        assert "reasoning" in capability_values
        assert "multimodal" in capability_values

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization (using default=str for enum)
        capability = EnumAgentCapability.CODE_REVIEW
        json_str = json.dumps(capability, default=str)
        # Note: default=str calls repr() which includes enum name
        assert "code_review" in json_str.lower()

        # Test in dictionary with value access
        data = {"capability": EnumAgentCapability.DOCUMENTATION.value}
        json_str = json.dumps(data)
        assert '"capability": "documentation"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class AgentCapabilityModel(BaseModel):
            capability: EnumAgentCapability

        # Test valid enum assignment
        model = AgentCapabilityModel(capability=EnumAgentCapability.CODE_GENERATION)
        assert model.capability == EnumAgentCapability.CODE_GENERATION

        # Test string assignment (should work due to str inheritance)
        model = AgentCapabilityModel(capability="security_analysis")
        assert model.capability == EnumAgentCapability.SECURITY_ANALYSIS

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            AgentCapabilityModel(capability="invalid_capability")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class AgentCapabilityModel(BaseModel):
            capability: EnumAgentCapability

        model = AgentCapabilityModel(capability=EnumAgentCapability.REASONING)

        # Test dict serialization
        model_dict = model.model_dump()
        assert model_dict == {"capability": "reasoning"}

        # Test JSON serialization
        json_str = model.model_dump_json()
        assert json_str == '{"capability":"reasoning"}'


@pytest.mark.unit
class TestEnumAgentCapabilityEdgeCases:
    """Test edge cases and error conditions."""

    def test_case_sensitivity(self):
        """Test that enum values are case-sensitive."""
        assert EnumAgentCapability.CODE_GENERATION.value == "code_generation"
        assert EnumAgentCapability.CODE_GENERATION.value != "CODE_GENERATION"
        assert EnumAgentCapability.CODE_GENERATION.value != "Code_Generation"

    def test_invalid_enum_creation(self):
        """Test that invalid enum values cannot be created."""
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumAgentCapability("invalid_capability")

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values are YAML serializable
        data = {"agent_capability": EnumAgentCapability.MULTIMODAL.value}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "agent_capability: multimodal" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["agent_capability"] == "multimodal"

        # Test that the enum value equals the string
        assert EnumAgentCapability.MULTIMODAL == "multimodal"

    def test_all_code_capabilities_have_code_prefix(self):
        """Test that all code-related capabilities have 'code_' prefix."""
        code_related = [c for c in EnumAgentCapability if c.is_code_related()]

        for capability in code_related:
            assert capability.value.startswith("code_"), (
                f"{capability} is code-related but doesn't have 'code_' prefix"
            )


@pytest.mark.unit
class TestEnumAgentCapabilityComprehensiveScenarios:
    """Test comprehensive real-world scenarios."""

    def test_agent_capability_selection(self):
        """Test selecting appropriate agent capabilities for different tasks."""
        # Simple code completion task
        quick_task_capability = EnumAgentCapability.CODE_COMPLETION
        assert quick_task_capability.is_code_related() is True
        assert quick_task_capability.requires_large_model() is False

        # Complex architecture task
        complex_task_capability = EnumAgentCapability.ARCHITECTURE_DESIGN
        assert complex_task_capability.is_code_related() is False
        assert complex_task_capability.requires_large_model() is True

    def test_capability_filtering_by_model_size(self):
        """Test filtering capabilities based on model size requirements."""
        # Get capabilities suitable for small models
        small_model_capabilities = [
            c for c in EnumAgentCapability if not c.requires_large_model()
        ]

        # Should have more small-model capabilities than large-model
        assert len(small_model_capabilities) > 0

        # Verify some expected capabilities
        assert EnumAgentCapability.FAST_INFERENCE in small_model_capabilities
        assert EnumAgentCapability.QUICK_VALIDATION in small_model_capabilities

        # Large model capabilities should not be in this list
        assert EnumAgentCapability.COMPLEX_ANALYSIS not in small_model_capabilities
        assert EnumAgentCapability.LONG_CONTEXT not in small_model_capabilities

    def test_capability_filtering_by_code_relation(self):
        """Test filtering capabilities based on code-relation."""
        # Get all code-related capabilities
        code_capabilities = [c for c in EnumAgentCapability if c.is_code_related()]

        # Should have exactly 5 code-related capabilities
        assert len(code_capabilities) == 5

        # Verify all expected code capabilities
        expected_code_caps = [
            EnumAgentCapability.CODE_GENERATION,
            EnumAgentCapability.CODE_REVIEW,
            EnumAgentCapability.CODE_REFACTORING,
            EnumAgentCapability.CODE_ANALYSIS,
            EnumAgentCapability.CODE_COMPLETION,
        ]

        for cap in expected_code_caps:
            assert cap in code_capabilities

    def test_multi_capability_agent_profile(self):
        """Test defining agent profiles with multiple capabilities."""
        # Define a comprehensive agent profile
        senior_dev_agent_caps = [
            EnumAgentCapability.CODE_GENERATION,
            EnumAgentCapability.CODE_REVIEW,
            EnumAgentCapability.ARCHITECTURE_DESIGN,
            EnumAgentCapability.SECURITY_ANALYSIS,
            EnumAgentCapability.DOCUMENTATION,
        ]

        # Verify all capabilities are valid
        for cap in senior_dev_agent_caps:
            assert cap in EnumAgentCapability

        # Check characteristics of this profile
        code_related_count = sum(
            1 for c in senior_dev_agent_caps if c.is_code_related()
        )
        large_model_count = sum(
            1 for c in senior_dev_agent_caps if c.requires_large_model()
        )

        assert code_related_count == 2  # CODE_GENERATION, CODE_REVIEW
        assert large_model_count == 1  # ARCHITECTURE_DESIGN

    def test_capability_categorization_coverage(self):
        """Test that all capabilities can be categorized by their properties."""
        all_capabilities = list(EnumAgentCapability)

        # Every capability should have a defined is_code_related result
        for cap in all_capabilities:
            result = cap.is_code_related()
            assert isinstance(result, bool)

        # Every capability should have a defined requires_large_model result
        for cap in all_capabilities:
            result = cap.requires_large_model()
            assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

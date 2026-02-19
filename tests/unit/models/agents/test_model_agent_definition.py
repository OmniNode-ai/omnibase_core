# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for agent definition models.

Tests cover validation behavior for all agent definition Pydantic models
including required/optional fields, frozen behavior, and extra field handling.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.agents import (
    ModelActivationPatterns,
    ModelAgentCapabilities,
    ModelAgentDefinition,
    ModelAgentIdentity,
    ModelAgentPhilosophy,
    ModelDomainQueries,
    ModelFrameworkIntegration,
    ModelIntegrationPoints,
    ModelIntelligenceIntegration,
    ModelOnexIntegration,
    ModelQualityGates,
    ModelSuccessMetrics,
    ModelTransformationContext,
    ModelWorkflowPhase,
    ModelWorkflowTemplates,
)


class TestModelAgentIdentity:
    """Tests for ModelAgentIdentity."""

    def test_minimal_valid_identity(self) -> None:
        """Test with only required fields."""
        identity = ModelAgentIdentity(
            name="test-agent",
            description="A test agent",
        )
        assert identity.name == "test-agent"
        assert identity.description == "A test agent"
        assert identity.title is None
        assert identity.color is None
        assert identity.task_agent_type is None
        assert identity.specialization_level is None
        assert identity.version is None
        assert identity.domain is None
        assert identity.short_name is None
        assert identity.aliases is None

    def test_full_identity(self) -> None:
        """Test with all fields populated."""
        identity = ModelAgentIdentity(
            name="test-agent",
            description="A test agent",
            title="Test Agent Title",
            color="blue",
            task_agent_type="testing",
            specialization_level="expert",
            version="1.0.0",
            domain="testing",
            short_name="ta",
            aliases=["tester", "qa"],
        )
        assert identity.title == "Test Agent Title"
        assert identity.color == "blue"
        assert identity.task_agent_type == "testing"
        assert identity.specialization_level == "expert"
        assert identity.version == "1.0.0"
        assert identity.domain == "testing"
        assert identity.short_name == "ta"
        assert identity.aliases == ["tester", "qa"]

    def test_missing_required_name_raises(self) -> None:
        """Test that missing name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentIdentity(description="Missing name")  # type: ignore[call-arg]
        assert "name" in str(exc_info.value)

    def test_missing_required_description_raises(self) -> None:
        """Test that missing description raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentIdentity(name="test")  # type: ignore[call-arg]
        assert "description" in str(exc_info.value)

    def test_frozen_model_raises_on_modification(self) -> None:
        """Test that frozen model cannot be modified."""
        identity = ModelAgentIdentity(name="test", description="test")
        with pytest.raises(ValidationError):
            identity.name = "modified"  # type: ignore[misc]

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are silently ignored."""
        identity = ModelAgentIdentity(
            name="test",
            description="test",
            unknown_field="should be ignored",  # type: ignore[call-arg]
        )
        assert identity.name == "test"
        assert not hasattr(identity, "unknown_field")

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate works correctly from dict."""
        data = {"name": "test-agent", "description": "test description"}
        identity = ModelAgentIdentity.model_validate(data)
        assert identity.name == "test-agent"
        assert identity.description == "test description"


class TestModelAgentPhilosophy:
    """Tests for ModelAgentPhilosophy."""

    def test_minimal_valid(self) -> None:
        """Test with only required field."""
        philosophy = ModelAgentPhilosophy(core_responsibility="Test things")
        assert philosophy.core_responsibility == "Test things"
        assert philosophy.core_purpose is None
        assert philosophy.principles is None
        assert philosophy.design_philosophy is None
        assert philosophy.methodology is None
        assert philosophy.context_philosophy is None

    def test_with_all_fields(self) -> None:
        """Test with all fields populated."""
        philosophy = ModelAgentPhilosophy(
            core_responsibility="Test things",
            core_purpose="Extended purpose",
            principles=["Be thorough", "Be fast"],
            design_philosophy=["Test-first", "Quality over speed"],
            methodology={"approach": "systematic"},
            context_philosophy=["Context aware"],
        )
        assert len(philosophy.principles) == 2
        assert philosophy.core_purpose == "Extended purpose"
        assert philosophy.methodology == {"approach": "systematic"}

    def test_missing_core_responsibility_raises(self) -> None:
        """Test that missing core_responsibility raises."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentPhilosophy(principles=["test"])  # type: ignore[call-arg]
        assert "core_responsibility" in str(exc_info.value)

    def test_frozen_model_raises_on_modification(self) -> None:
        """Test that frozen model cannot be modified."""
        philosophy = ModelAgentPhilosophy(core_responsibility="Test")
        with pytest.raises(ValidationError):
            philosophy.core_responsibility = "modified"  # type: ignore[misc]

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are silently ignored."""
        philosophy = ModelAgentPhilosophy(
            core_responsibility="Test",
            unknown="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(philosophy, "unknown")


class TestModelAgentCapabilities:
    """Tests for ModelAgentCapabilities."""

    def test_minimal_valid(self) -> None:
        """Test with only required field."""
        caps = ModelAgentCapabilities(primary=["capability1", "capability2"])
        assert len(caps.primary) == 2
        assert caps.secondary is None
        assert caps.specialized is None

    def test_full_capabilities(self) -> None:
        """Test with all fields."""
        caps = ModelAgentCapabilities(
            primary=["cap1"],
            secondary=["cap2"],
            specialized=["cap3"],
        )
        assert caps.primary == ["cap1"]
        assert caps.secondary == ["cap2"]
        assert caps.specialized == ["cap3"]

    def test_missing_primary_raises(self) -> None:
        """Test that missing primary raises."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentCapabilities(secondary=["test"])  # type: ignore[call-arg]
        assert "primary" in str(exc_info.value)

    def test_empty_primary_allowed(self) -> None:
        """Test that empty primary list is allowed (no min_length constraint)."""
        caps = ModelAgentCapabilities(primary=[])
        assert caps.primary == []

    def test_frozen_model_raises_on_modification(self) -> None:
        """Test that frozen model cannot be modified."""
        caps = ModelAgentCapabilities(primary=["cap1"])
        with pytest.raises(ValidationError):
            caps.primary = ["modified"]  # type: ignore[misc]


class TestModelOnexIntegration:
    """Tests for ModelOnexIntegration."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        integration = ModelOnexIntegration()
        assert integration.strong_typing is None
        assert integration.error_handling is None
        assert integration.naming_conventions is None
        assert integration.contract_driven is None
        assert integration.registry_pattern is None
        assert integration.four_node_architecture is None

    def test_full_integration(self) -> None:
        """Test with all fields populated."""
        integration = ModelOnexIntegration(
            strong_typing="Required",
            error_handling="Strict",
            naming_conventions="snake_case",
            contract_driven="Always",
            registry_pattern="Singleton",
            four_node_architecture={
                "EFFECT": "External I/O",
                "COMPUTE": "Pure transforms",
            },
        )
        assert integration.strong_typing == "Required"
        assert integration.four_node_architecture["EFFECT"] == "External I/O"

    def test_frozen_model_raises_on_modification(self) -> None:
        """Test that frozen model cannot be modified."""
        integration = ModelOnexIntegration(strong_typing="Required")
        with pytest.raises(ValidationError):
            integration.strong_typing = "Optional"  # type: ignore[misc]


class TestModelDomainQueries:
    """Tests for ModelDomainQueries."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        queries = ModelDomainQueries()
        assert queries.domain is None
        assert queries.implementation is None

    def test_full_domain_queries(self) -> None:
        """Test with all fields populated."""
        queries = ModelDomainQueries(
            domain="testing",
            implementation="query_engine",
        )
        assert queries.domain == "testing"
        assert queries.implementation == "query_engine"


class TestModelFrameworkIntegration:
    """Tests for ModelFrameworkIntegration."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        framework = ModelFrameworkIntegration()
        assert framework.yaml_framework_references is None
        assert framework.domain_queries is None
        assert framework.mandatory_functions is None
        assert framework.pattern_catalog is None

    def test_full_framework_integration(self) -> None:
        """Test with all fields populated."""
        framework = ModelFrameworkIntegration(
            yaml_framework_references=["@spec.yaml", "@types.yaml"],
            domain_queries=ModelDomainQueries(domain="test"),
            mandatory_functions=["init()", "process()"],
            pattern_catalog={"singleton": {"description": "Single instance"}},
        )
        assert len(framework.yaml_framework_references) == 2
        assert framework.domain_queries.domain == "test"
        assert framework.mandatory_functions == ["init()", "process()"]

    def test_nested_domain_queries(self) -> None:
        """Test that nested ModelDomainQueries works correctly."""
        framework = ModelFrameworkIntegration(
            domain_queries=ModelDomainQueries(
                domain="code_analysis",
                implementation="ast_parser",
            ),
        )
        assert framework.domain_queries.domain == "code_analysis"
        assert framework.domain_queries.implementation == "ast_parser"


class TestModelIntelligenceIntegration:
    """Tests for ModelIntelligenceIntegration."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        intel = ModelIntelligenceIntegration()
        assert intel.quality_assessment is None
        assert intel.performance_optimization is None
        assert intel.codanna_integration is None

    def test_full_intelligence_integration(self) -> None:
        """Test with all fields populated."""
        intel = ModelIntelligenceIntegration(
            quality_assessment=["assess_quality()", "check_standards()"],
            performance_optimization=["optimize_queries()"],
            codanna_integration={
                "primary_method": "mcp__codanna__analyze",
                "capabilities": ["symbol_search", "impact_analysis"],
            },
        )
        assert len(intel.quality_assessment) == 2
        assert intel.codanna_integration["primary_method"] == "mcp__codanna__analyze"


class TestModelActivationPatterns:
    """Tests for ModelActivationPatterns."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        patterns = ModelActivationPatterns()
        assert patterns.explicit_triggers is None
        assert patterns.context_triggers is None
        assert patterns.capability_matching is None
        assert patterns.activation_keywords is None
        assert patterns.aliases is None

    def test_full_activation_patterns(self) -> None:
        """Test with all fields populated."""
        patterns = ModelActivationPatterns(
            explicit_triggers=["test", "qa", "verify"],
            context_triggers=["testing context", "quality assurance"],
            capability_matching=["test_*", "verify_*"],
            activation_keywords=["test", "check"],
            aliases=["tester", "validator"],
        )
        assert len(patterns.explicit_triggers) == 3
        assert "testing context" in patterns.context_triggers


class TestModelWorkflowPhase:
    """Tests for ModelWorkflowPhase."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        phase = ModelWorkflowPhase()
        assert phase.function_name is None
        assert phase.phases is None

    def test_full_workflow_phase(self) -> None:
        """Test with all fields populated."""
        phase = ModelWorkflowPhase(
            function_name="init_workflow",
            phases=["prepare", "execute", "validate"],
        )
        assert phase.function_name == "init_workflow"
        assert len(phase.phases) == 3


class TestModelWorkflowTemplates:
    """Tests for ModelWorkflowTemplates."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        templates = ModelWorkflowTemplates()
        assert templates.initialization is None
        assert templates.intelligence_gathering is None
        assert templates.task_execution is None
        assert templates.context_execution is None
        assert templates.knowledge_capture is None

    def test_full_workflow_templates(self) -> None:
        """Test with all fields populated."""
        templates = ModelWorkflowTemplates(
            initialization=ModelWorkflowPhase(
                function_name="init",
                phases=["setup"],
            ),
            intelligence_gathering=ModelWorkflowPhase(
                function_name="gather_intel",
                phases=["scan", "analyze"],
            ),
            task_execution=ModelWorkflowPhase(
                function_name="execute",
                phases=["run"],
            ),
            context_execution=ModelWorkflowPhase(
                function_name="context_exec",
            ),
            knowledge_capture=ModelWorkflowPhase(
                function_name="capture",
            ),
        )
        assert templates.initialization.function_name == "init"
        assert templates.intelligence_gathering.phases == ["scan", "analyze"]


class TestModelQualityGates:
    """Tests for ModelQualityGates."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        gates = ModelQualityGates()
        assert gates.must_have_requirements is None
        assert gates.quality_standards is None

    def test_full_quality_gates(self) -> None:
        """Test with all fields populated."""
        gates = ModelQualityGates(
            must_have_requirements=["tests_pass", "coverage_60"],
            quality_standards=["no_lint_errors", "type_checked"],
        )
        assert len(gates.must_have_requirements) == 2
        assert "type_checked" in gates.quality_standards


class TestModelSuccessMetrics:
    """Tests for ModelSuccessMetrics."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        metrics = ModelSuccessMetrics()
        assert metrics.performance_targets is None
        assert metrics.intelligence_enhanced_outcomes is None

    def test_full_success_metrics(self) -> None:
        """Test with all fields populated."""
        metrics = ModelSuccessMetrics(
            performance_targets={
                "latency_ms": 100,
                "throughput": 1000,
            },
            intelligence_enhanced_outcomes=["improved_accuracy", "faster_delivery"],
        )
        assert metrics.performance_targets["latency_ms"] == 100
        assert len(metrics.intelligence_enhanced_outcomes) == 2


class TestModelIntegrationPoints:
    """Tests for ModelIntegrationPoints."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        points = ModelIntegrationPoints()
        assert points.complementary_agents is None
        assert points.collaboration_patterns is None

    def test_full_integration_points(self) -> None:
        """Test with all fields populated."""
        points = ModelIntegrationPoints(
            complementary_agents=["agent-reviewer", "agent-deployer"],
            collaboration_patterns=["handoff", "parallel"],
        )
        assert len(points.complementary_agents) == 2
        assert "handoff" in points.collaboration_patterns


class TestModelTransformationContext:
    """Tests for ModelTransformationContext."""

    def test_minimal_valid_empty(self) -> None:
        """Test that all fields are optional."""
        context = ModelTransformationContext()
        assert context.identity_assumption_triggers is None
        assert context.capability_inheritance is None
        assert context.execution_context is None
        assert context.migration_from is None
        assert context.migration_to is None

    def test_full_transformation_context(self) -> None:
        """Test with all fields populated."""
        context = ModelTransformationContext(
            identity_assumption_triggers=["become_reviewer", "transform"],
            capability_inheritance=["base_capabilities", "review_caps"],
            execution_context=["code_review", "pr_context"],
            migration_from="agent-v1",
            migration_to="agent-v2",
        )
        assert len(context.identity_assumption_triggers) == 2
        assert context.migration_from == "agent-v1"
        assert context.migration_to == "agent-v2"


class TestModelAgentDefinition:
    """Tests for the top-level ModelAgentDefinition."""

    @pytest.fixture
    def minimal_agent_data(self) -> dict:
        """Minimal valid agent data."""
        return {
            "schema_version": "1.0.0",
            "agent_type": "test_agent",
            "agent_identity": {
                "name": "test-agent",
                "description": "A test agent",
            },
            "onex_integration": {
                "strong_typing": "Required",
            },
            "agent_philosophy": {
                "core_responsibility": "Testing",
            },
            "capabilities": {
                "primary": ["test capability"],
            },
            "intelligence_integration": {
                "quality_assessment": ["assess_quality()"],
            },
        }

    def test_minimal_valid_agent(self, minimal_agent_data: dict) -> None:
        """Test minimal valid agent definition."""
        agent = ModelAgentDefinition.model_validate(minimal_agent_data)
        assert agent.schema_version == "1.0.0"
        assert agent.agent_type == "test_agent"
        assert agent.agent_identity.name == "test-agent"
        assert agent.agent_identity.description == "A test agent"
        assert agent.onex_integration.strong_typing == "Required"
        assert agent.agent_philosophy.core_responsibility == "Testing"
        assert agent.capabilities.primary == ["test capability"]
        assert agent.intelligence_integration.quality_assessment == ["assess_quality()"]

    def test_optional_fields_default_to_none(self, minimal_agent_data: dict) -> None:
        """Test that optional fields default to None."""
        agent = ModelAgentDefinition.model_validate(minimal_agent_data)
        assert agent.definition_format is None
        assert agent.framework_integration is None
        assert agent.claude_skills_references is None
        assert agent.activation_patterns is None
        assert agent.workflow_templates is None
        assert agent.quality_gates is None
        assert agent.success_metrics is None
        assert agent.integration_points is None
        assert agent.transformation_context is None

    def test_full_agent_with_all_fields(self, minimal_agent_data: dict) -> None:
        """Test agent with all optional fields."""
        full_data = {
            **minimal_agent_data,
            "definition_format": "yaml_agent_v1",
            "framework_integration": {
                "yaml_framework_references": ["@spec.yaml"],
                "mandatory_functions": ["func1()"],
            },
            "claude_skills_references": ["@skill1", "@skill2"],
            "activation_patterns": {
                "explicit_triggers": ["test", "qa"],
                "context_triggers": ["testing context"],
            },
            "workflow_templates": {
                "initialization": {
                    "function_name": "init_test",
                    "phases": ["phase1", "phase2"],
                },
            },
            "quality_gates": {
                "must_have_requirements": ["req1"],
                "quality_standards": ["standard1"],
            },
            "success_metrics": {
                "performance_targets": {"latency_ms": 100},
            },
            "integration_points": {
                "complementary_agents": ["agent1"],
                "collaboration_patterns": ["pattern1"],
            },
            "transformation_context": {
                "identity_assumption_triggers": ["trigger1"],
                "capability_inheritance": ["inherit1"],
            },
        }
        agent = ModelAgentDefinition.model_validate(full_data)
        assert agent.definition_format == "yaml_agent_v1"
        assert agent.framework_integration.yaml_framework_references == ["@spec.yaml"]
        assert agent.claude_skills_references == ["@skill1", "@skill2"]
        assert agent.activation_patterns.explicit_triggers == ["test", "qa"]
        assert agent.workflow_templates.initialization.function_name == "init_test"
        assert agent.workflow_templates.initialization.phases == ["phase1", "phase2"]
        assert agent.quality_gates.must_have_requirements == ["req1"]
        assert agent.success_metrics.performance_targets == {"latency_ms": 100}
        assert agent.integration_points.complementary_agents == ["agent1"]
        assert agent.transformation_context.identity_assumption_triggers == ["trigger1"]

    def test_unknown_sections_silently_ignored(self, minimal_agent_data: dict) -> None:
        """Test that unknown sections are silently ignored (extra='ignore').

        Agent-specific sections like review_framework are handled by
        extra='ignore' which allows forward compatibility with new fields.
        """
        data_with_unknown_sections = {
            **minimal_agent_data,
            "review_framework": {"severity_levels": ["critical", "major"]},
            "custom_section": {"key": "value"},
        }
        # Should not raise - unknown fields are ignored
        agent = ModelAgentDefinition.model_validate(data_with_unknown_sections)
        assert agent.schema_version == "1.0.0"
        # Unknown fields are not accessible (by design)
        assert not hasattr(agent, "review_framework")
        assert not hasattr(agent, "custom_section")

    def test_missing_required_schema_version_raises(
        self, minimal_agent_data: dict
    ) -> None:
        """Test missing schema_version raises ValidationError."""
        del minimal_agent_data["schema_version"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentDefinition.model_validate(minimal_agent_data)
        assert "schema_version" in str(exc_info.value)

    def test_missing_required_agent_type_raises(self, minimal_agent_data: dict) -> None:
        """Test missing agent_type raises ValidationError."""
        del minimal_agent_data["agent_type"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentDefinition.model_validate(minimal_agent_data)
        assert "agent_type" in str(exc_info.value)

    def test_missing_required_agent_identity_raises(
        self, minimal_agent_data: dict
    ) -> None:
        """Test missing agent_identity raises ValidationError."""
        del minimal_agent_data["agent_identity"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentDefinition.model_validate(minimal_agent_data)
        assert "agent_identity" in str(exc_info.value)

    def test_missing_required_onex_integration_raises(
        self, minimal_agent_data: dict
    ) -> None:
        """Test missing onex_integration raises ValidationError."""
        del minimal_agent_data["onex_integration"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentDefinition.model_validate(minimal_agent_data)
        assert "onex_integration" in str(exc_info.value)

    def test_missing_required_agent_philosophy_raises(
        self, minimal_agent_data: dict
    ) -> None:
        """Test missing agent_philosophy raises ValidationError."""
        del minimal_agent_data["agent_philosophy"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentDefinition.model_validate(minimal_agent_data)
        assert "agent_philosophy" in str(exc_info.value)

    def test_missing_required_capabilities_raises(
        self, minimal_agent_data: dict
    ) -> None:
        """Test missing capabilities raises ValidationError."""
        del minimal_agent_data["capabilities"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentDefinition.model_validate(minimal_agent_data)
        assert "capabilities" in str(exc_info.value)

    def test_missing_required_intelligence_integration_raises(
        self, minimal_agent_data: dict
    ) -> None:
        """Test missing intelligence_integration raises ValidationError."""
        del minimal_agent_data["intelligence_integration"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentDefinition.model_validate(minimal_agent_data)
        assert "intelligence_integration" in str(exc_info.value)

    def test_extra_top_level_fields_ignored(self, minimal_agent_data: dict) -> None:
        """Test that unknown top-level fields are ignored."""
        minimal_agent_data["unknown_section"] = {"foo": "bar"}
        agent = ModelAgentDefinition.model_validate(minimal_agent_data)
        assert agent.schema_version == "1.0.0"
        assert not hasattr(agent, "unknown_section")

    def test_frozen_raises_on_modification(self, minimal_agent_data: dict) -> None:
        """Test that frozen model cannot be modified."""
        agent = ModelAgentDefinition.model_validate(minimal_agent_data)
        with pytest.raises(ValidationError):
            agent.schema_version = "2.0.0"  # type: ignore[misc]

    def test_model_validate_from_dict(self, minimal_agent_data: dict) -> None:
        """Test model_validate works correctly."""
        agent = ModelAgentDefinition.model_validate(minimal_agent_data)
        assert isinstance(agent, ModelAgentDefinition)
        assert isinstance(agent.agent_identity, ModelAgentIdentity)
        assert isinstance(agent.agent_philosophy, ModelAgentPhilosophy)
        assert isinstance(agent.capabilities, ModelAgentCapabilities)
        assert isinstance(agent.onex_integration, ModelOnexIntegration)
        assert isinstance(agent.intelligence_integration, ModelIntelligenceIntegration)

    def test_nested_validation_errors_propagate(self, minimal_agent_data: dict) -> None:
        """Test that validation errors in nested models propagate correctly."""
        # Remove required field from nested model
        minimal_agent_data["agent_identity"] = {"name": "test"}  # Missing description
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentDefinition.model_validate(minimal_agent_data)
        assert "description" in str(exc_info.value)

    def test_nested_extra_fields_ignored(self, minimal_agent_data: dict) -> None:
        """Test that extra fields in nested models are also ignored."""
        minimal_agent_data["agent_identity"]["unknown_nested"] = "ignored"
        agent = ModelAgentDefinition.model_validate(minimal_agent_data)
        assert not hasattr(agent.agent_identity, "unknown_nested")

    def test_empty_optional_nested_models_allowed(
        self, minimal_agent_data: dict
    ) -> None:
        """Test that empty dicts for optional nested models work."""
        minimal_agent_data["activation_patterns"] = {}
        minimal_agent_data["quality_gates"] = {}
        agent = ModelAgentDefinition.model_validate(minimal_agent_data)
        assert agent.activation_patterns is not None
        assert agent.activation_patterns.explicit_triggers is None
        assert agent.quality_gates is not None
        assert agent.quality_gates.must_have_requirements is None

    def test_from_attributes_true_allows_object_init(
        self, minimal_agent_data: dict
    ) -> None:
        """Test that from_attributes=True enables ORM-style instantiation."""
        # First create a valid agent
        agent = ModelAgentDefinition.model_validate(minimal_agent_data)
        # Then validate from the model instance (from_attributes=True)
        agent_copy = ModelAgentDefinition.model_validate(agent)
        assert agent_copy.schema_version == agent.schema_version
        assert agent_copy.agent_identity.name == agent.agent_identity.name

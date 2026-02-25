# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelRagQueries and to_routing_config converter.

Covers:
- ModelRagQueries field validation (confidence_threshold, match_count)
- ModelRagQueries frozen / extra-ignore behaviour
- to_routing_config() extraction from ModelAgentDefinition
- Round-trip: YAML-like dict -> ModelAgentDefinition -> to_routing_config()
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
    ModelFrameworkIntegration,
    ModelIntelligenceIntegration,
    ModelOnexIntegration,
    ModelRagQueries,
    to_routing_config,
)

# ---------------------------------------------------------------------------
# ModelRagQueries tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelRagQueries:
    """Tests for ModelRagQueries field-level validation."""

    def test_empty_model_is_valid(self) -> None:
        """All fields are optional — empty construction must succeed."""
        rq = ModelRagQueries()
        assert rq.domain_query is None
        assert rq.implementation_query is None
        assert rq.context_preference is None
        assert rq.match_count is None
        assert rq.confidence_threshold is None

    def test_full_model_valid(self) -> None:
        """Typical agent YAML values should parse cleanly."""
        rq = ModelRagQueries(
            domain_query="engineering metrics",
            implementation_query="velocity tracking patterns",
            context_preference="debugging",
            match_count=5,
            confidence_threshold=0.6,
        )
        assert rq.domain_query == "engineering metrics"
        assert rq.match_count == 5
        assert rq.confidence_threshold == 0.6

    # match_count validation

    def test_match_count_boundary_min(self) -> None:
        """match_count=1 is the minimum allowed value."""
        rq = ModelRagQueries(match_count=1)
        assert rq.match_count == 1

    def test_match_count_boundary_max(self) -> None:
        """match_count=20 is the maximum allowed value."""
        rq = ModelRagQueries(match_count=20)
        assert rq.match_count == 20

    def test_match_count_zero_raises(self) -> None:
        """match_count=0 is below the minimum — must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRagQueries(match_count=0)
        assert "match_count" in str(exc_info.value)

    def test_match_count_negative_raises(self) -> None:
        """Negative match_count must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRagQueries(match_count=-1)
        assert "match_count" in str(exc_info.value)

    def test_match_count_above_max_raises(self) -> None:
        """match_count=21 exceeds the maximum — must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRagQueries(match_count=21)
        assert "match_count" in str(exc_info.value)

    def test_match_count_none_allowed(self) -> None:
        """Explicit None for match_count must not raise."""
        rq = ModelRagQueries(match_count=None)
        assert rq.match_count is None

    # confidence_threshold validation

    def test_confidence_threshold_zero(self) -> None:
        """confidence_threshold=0.0 is the minimum allowed value."""
        rq = ModelRagQueries(confidence_threshold=0.0)
        assert rq.confidence_threshold == 0.0

    def test_confidence_threshold_one(self) -> None:
        """confidence_threshold=1.0 is the maximum allowed value."""
        rq = ModelRagQueries(confidence_threshold=1.0)
        assert rq.confidence_threshold == 1.0

    def test_confidence_threshold_typical(self) -> None:
        """Typical value 0.6 used by most agent YAMLs."""
        rq = ModelRagQueries(confidence_threshold=0.6)
        assert rq.confidence_threshold == 0.6

    def test_confidence_threshold_negative_raises(self) -> None:
        """confidence_threshold < 0.0 must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRagQueries(confidence_threshold=-0.1)
        assert "confidence_threshold" in str(exc_info.value)

    def test_confidence_threshold_above_one_raises(self) -> None:
        """confidence_threshold > 1.0 must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRagQueries(confidence_threshold=1.01)
        assert "confidence_threshold" in str(exc_info.value)

    def test_confidence_threshold_none_allowed(self) -> None:
        """Explicit None for confidence_threshold must not raise."""
        rq = ModelRagQueries(confidence_threshold=None)
        assert rq.confidence_threshold is None

    # Frozen / extra-ignore behaviour

    def test_frozen_raises_on_modification(self) -> None:
        """ModelRagQueries is frozen — mutation must raise."""
        rq = ModelRagQueries(match_count=5)
        with pytest.raises(ValidationError):
            rq.match_count = 10

    def test_extra_fields_ignored(self) -> None:
        """Unknown fields from agent YAMLs must be silently ignored."""
        rq = ModelRagQueries(
            match_count=5,
            confidence_threshold=0.7,
            unknown_future_field="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(rq, "unknown_future_field")
        assert rq.match_count == 5

    def test_model_validate_from_dict(self) -> None:
        """model_validate from a plain dict (as parsed from YAML) must work."""
        data = {
            "domain_query": "engineering velocity",
            "implementation_query": "metrics tracking",
            "context_preference": "debugging",
            "match_count": 5,
            "confidence_threshold": 0.6,
        }
        rq = ModelRagQueries.model_validate(data)
        assert rq.domain_query == "engineering velocity"
        assert rq.match_count == 5
        assert rq.confidence_threshold == 0.6


# ---------------------------------------------------------------------------
# Helpers shared by to_routing_config tests
# ---------------------------------------------------------------------------


def _make_minimal_definition(
    *,
    name: str = "test-agent",
    agent_type: str = "test",
    primary_capabilities: list[str] | None = None,
) -> ModelAgentDefinition:
    """Build a minimal valid ModelAgentDefinition for converter tests."""
    return ModelAgentDefinition(
        schema_version="1.0.0",
        agent_type=agent_type,
        agent_identity=ModelAgentIdentity(
            name=name,
            description="A test agent",
        ),
        onex_integration=ModelOnexIntegration(),
        agent_philosophy=ModelAgentPhilosophy(core_responsibility="Testing"),
        capabilities=ModelAgentCapabilities(
            primary=primary_capabilities
            if primary_capabilities is not None
            else ["capability-one"],
        ),
        intelligence_integration=ModelIntelligenceIntegration(),
    )


# ---------------------------------------------------------------------------
# to_routing_config() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestToRoutingConfig:
    """Tests for the to_routing_config() converter function."""

    def test_minimal_definition_produces_valid_routing_config(self) -> None:
        """Minimal definition must produce a well-formed routing dict."""
        agent = _make_minimal_definition()
        routing = to_routing_config(agent)

        assert routing["name"] == "test-agent"
        assert routing["agent_type"] == "test"
        assert routing["description"] == "A test agent"
        assert routing["title"] is None
        assert routing["domain"] is None
        assert routing["aliases"] == []
        assert routing["activation_keywords"] == []
        assert routing["explicit_triggers"] == []
        assert routing["context_triggers"] == []
        assert routing["primary_capabilities"] == ["capability-one"]
        assert routing["match_count"] is None
        assert routing["confidence_threshold"] is None
        assert routing["skills"] == []

    def test_primary_capabilities_preserved(self) -> None:
        """Primary capabilities list must pass through unchanged."""
        agent = _make_minimal_definition(
            primary_capabilities=["code review", "security analysis", "perf profiling"]
        )
        routing = to_routing_config(agent)
        assert routing["primary_capabilities"] == [
            "code review",
            "security analysis",
            "perf profiling",
        ]

    def test_activation_patterns_extracted(self) -> None:
        """Activation triggers must be extracted from activation_patterns."""
        agent = _make_minimal_definition()
        # Build a definition with activation_patterns set
        agent_with_activation = ModelAgentDefinition(
            schema_version="1.0.0",
            agent_type="test",
            agent_identity=ModelAgentIdentity(
                name="test-agent",
                description="Test agent",
                aliases=["tester", "qa-bot"],
            ),
            onex_integration=ModelOnexIntegration(),
            agent_philosophy=ModelAgentPhilosophy(core_responsibility="Testing"),
            capabilities=ModelAgentCapabilities(primary=["test"]),
            intelligence_integration=ModelIntelligenceIntegration(),
            activation_patterns=ModelActivationPatterns(
                explicit_triggers=["run tests", "test suite"],
                context_triggers=["testing context"],
                activation_keywords=["test", "qa"],
            ),
        )
        routing = to_routing_config(agent_with_activation)

        assert routing["explicit_triggers"] == ["run tests", "test suite"]
        assert routing["context_triggers"] == ["testing context"]
        assert routing["activation_keywords"] == ["test", "qa"]
        assert routing["aliases"] == ["tester", "qa-bot"]

    def test_rag_queries_extracted_from_framework_integration(self) -> None:
        """match_count and confidence_threshold come from framework.rag_queries."""
        agent = ModelAgentDefinition(
            schema_version="1.0.0",
            agent_type="rag_agent",
            agent_identity=ModelAgentIdentity(
                name="rag-agent",
                description="RAG-enabled agent",
            ),
            onex_integration=ModelOnexIntegration(),
            agent_philosophy=ModelAgentPhilosophy(core_responsibility="RAG retrieval"),
            capabilities=ModelAgentCapabilities(primary=["rag retrieval"]),
            intelligence_integration=ModelIntelligenceIntegration(),
            framework_integration=ModelFrameworkIntegration(
                rag_queries=ModelRagQueries(
                    domain_query="engineering metrics velocity",
                    implementation_query="velocity patterns",
                    context_preference="debugging",
                    match_count=5,
                    confidence_threshold=0.6,
                ),
            ),
        )
        routing = to_routing_config(agent)

        assert routing["match_count"] == 5
        assert routing["confidence_threshold"] == 0.6

    def test_no_rag_queries_yields_none_values(self) -> None:
        """When framework_integration has no rag_queries, both fields are None."""
        agent = ModelAgentDefinition(
            schema_version="1.0.0",
            agent_type="test",
            agent_identity=ModelAgentIdentity(name="agent", description="Agent"),
            onex_integration=ModelOnexIntegration(),
            agent_philosophy=ModelAgentPhilosophy(core_responsibility="Testing"),
            capabilities=ModelAgentCapabilities(primary=["capability"]),
            intelligence_integration=ModelIntelligenceIntegration(),
            framework_integration=ModelFrameworkIntegration(),  # no rag_queries
        )
        routing = to_routing_config(agent)

        assert routing["match_count"] is None
        assert routing["confidence_threshold"] is None

    def test_skills_references_extracted(self) -> None:
        """claude_skills_references must pass through as 'skills' key."""
        agent = ModelAgentDefinition(
            schema_version="1.0.0",
            agent_type="test",
            agent_identity=ModelAgentIdentity(name="agent", description="Agent"),
            onex_integration=ModelOnexIntegration(),
            agent_philosophy=ModelAgentPhilosophy(core_responsibility="Testing"),
            capabilities=ModelAgentCapabilities(primary=["skill1"]),
            intelligence_integration=ModelIntelligenceIntegration(),
            claude_skills_references=["@skill-a", "@skill-b"],
        )
        routing = to_routing_config(agent)

        assert routing["skills"] == ["@skill-a", "@skill-b"]

    def test_round_trip_yaml_dict_to_routing_config(self) -> None:
        """Full round-trip: YAML-like dict -> ModelAgentDefinition -> routing."""
        yaml_like_data = {
            "schema_version": "1.0.0",
            "agent_type": "velocity_tracker",
            "agent_identity": {
                "name": "agent-velocity-tracker",
                "title": "Velocity Tracker Agent",
                "description": "Tracks engineering velocity metrics",
                "domain": "engineering_productivity",
                "aliases": ["velocity", "tracker"],
            },
            "onex_integration": {"strong_typing": "Required"},
            "agent_philosophy": {
                "core_responsibility": "Track and report engineering velocity"
            },
            "capabilities": {
                "primary": ["velocity tracking", "metrics collection"],
                "secondary": ["reporting", "alerting"],
            },
            "intelligence_integration": {"quality_assessment": ["assess_velocity()"]},
            "activation_patterns": {
                "explicit_triggers": ["track velocity", "velocity report"],
                "context_triggers": ["engineering metrics context"],
                "activation_keywords": ["velocity", "metrics"],
            },
            "framework_integration": {
                "rag_queries": {
                    "domain_query": "engineering productivity metrics",
                    "implementation_query": "velocity tracking patterns",
                    "context_preference": "debugging",
                    "match_count": 5,
                    "confidence_threshold": 0.6,
                }
            },
            "claude_skills_references": ["@remembering-conversations"],
        }

        agent = ModelAgentDefinition.model_validate(yaml_like_data)
        routing = to_routing_config(agent)

        assert routing["name"] == "agent-velocity-tracker"
        assert routing["agent_type"] == "velocity_tracker"
        assert routing["title"] == "Velocity Tracker Agent"
        assert routing["domain"] == "engineering_productivity"
        assert routing["aliases"] == ["velocity", "tracker"]
        assert routing["explicit_triggers"] == ["track velocity", "velocity report"]
        assert routing["context_triggers"] == ["engineering metrics context"]
        assert routing["activation_keywords"] == ["velocity", "metrics"]
        assert routing["primary_capabilities"] == [
            "velocity tracking",
            "metrics collection",
        ]
        assert routing["match_count"] == 5
        assert routing["confidence_threshold"] == 0.6
        assert routing["skills"] == ["@remembering-conversations"]

    def test_routing_config_contains_required_keys(self) -> None:
        """Routing config dict must always contain all expected keys."""
        agent = _make_minimal_definition()
        routing = to_routing_config(agent)

        required_keys = {
            "name",
            "agent_type",
            "description",
            "title",
            "domain",
            "aliases",
            "activation_keywords",
            "explicit_triggers",
            "context_triggers",
            "primary_capabilities",
            "match_count",
            "confidence_threshold",
            "skills",
        }
        assert required_keys.issubset(routing.keys())

    def test_empty_optional_lists_default_to_empty_lists(self) -> None:
        """None optional lists in the model must become [] in routing config."""
        agent = _make_minimal_definition()
        routing = to_routing_config(agent)

        assert isinstance(routing["aliases"], list)
        assert isinstance(routing["activation_keywords"], list)
        assert isinstance(routing["explicit_triggers"], list)
        assert isinstance(routing["context_triggers"], list)
        assert isinstance(routing["skills"], list)

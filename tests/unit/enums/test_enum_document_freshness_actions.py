"""
Unit tests for Document Freshness enums.

Tests all document freshness-related enums including:
- EnumDocumentFreshnessActions
- EnumDocumentFreshnessRiskLevel
- EnumDocumentFreshnessStatus
- EnumDocumentType
- EnumRecommendationType
- EnumRecommendationPriority
- EnumEstimatedEffort
- EnumDependencyRelationship
- EnumOutputFormat

Tests cover:
- Enum value validation
- String representation
- JSON/YAML serialization
- Pydantic integration
- Edge cases
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_document_freshness_actions import (
    EnumDependencyRelationship,
    EnumDocumentFreshnessActions,
    EnumDocumentFreshnessRiskLevel,
    EnumDocumentFreshnessStatus,
    EnumDocumentType,
    EnumEstimatedEffort,
    EnumOutputFormat,
    EnumRecommendationPriority,
    EnumRecommendationType,
)


class TestEnumDocumentFreshnessActions:
    """Test EnumDocumentFreshnessActions enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "MONITOR_FRESHNESS": "monitor_freshness",
            "ANALYZE_DEPENDENCIES": "analyze_dependencies",
            "DETECT_CHANGES": "detect_changes",
            "AI_SEMANTIC_ANALYSIS": "ai_semantic_analysis",
            "GENERATE_AUDIT_REPORT": "generate_audit_report",
            "HEALTH_CHECK": "health_check",
            "CONNECTION_POOL_METRICS": "connection_pool_metrics",
        }

        for name, value in expected_values.items():
            action = getattr(EnumDocumentFreshnessActions, name)
            assert action.value == value

    def test_string_equality(self):
        """Test that enum values equal their string representations."""
        assert EnumDocumentFreshnessActions.MONITOR_FRESHNESS == "monitor_freshness"
        assert (
            EnumDocumentFreshnessActions.AI_SEMANTIC_ANALYSIS == "ai_semantic_analysis"
        )

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        actions = list(EnumDocumentFreshnessActions)
        assert len(actions) == 7

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class ActionModel(BaseModel):
            action: EnumDocumentFreshnessActions

        model = ActionModel(action=EnumDocumentFreshnessActions.MONITOR_FRESHNESS)
        assert model.action == EnumDocumentFreshnessActions.MONITOR_FRESHNESS

        # Test string assignment
        model = ActionModel(action="detect_changes")
        assert model.action == EnumDocumentFreshnessActions.DETECT_CHANGES


class TestEnumDocumentFreshnessRiskLevel:
    """Test EnumDocumentFreshnessRiskLevel enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "LOW": "low",
            "MEDIUM": "medium",
            "HIGH": "high",
            "CRITICAL": "critical",
        }

        for name, value in expected_values.items():
            risk_level = getattr(EnumDocumentFreshnessRiskLevel, name)
            assert risk_level.value == value

    def test_risk_level_ordering(self):
        """Test that risk levels can be compared for severity."""
        # Get all risk levels in definition order
        levels = list(EnumDocumentFreshnessRiskLevel)
        assert len(levels) == 4

        # Verify expected order (low to critical)
        assert levels[0] == EnumDocumentFreshnessRiskLevel.LOW
        assert levels[-1] == EnumDocumentFreshnessRiskLevel.CRITICAL

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class RiskModel(BaseModel):
            risk: EnumDocumentFreshnessRiskLevel

        model = RiskModel(risk=EnumDocumentFreshnessRiskLevel.HIGH)
        assert model.risk == EnumDocumentFreshnessRiskLevel.HIGH

        # Test invalid value
        with pytest.raises(ValidationError):
            RiskModel(risk="invalid_risk")


class TestEnumDocumentFreshnessStatus:
    """Test EnumDocumentFreshnessStatus enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "FRESH": "fresh",
            "STALE": "stale",
            "CRITICAL": "critical",
            "UNKNOWN": "unknown",
        }

        for name, value in expected_values.items():
            status = getattr(EnumDocumentFreshnessStatus, name)
            assert status.value == value

    def test_status_states(self):
        """Test different status states."""
        assert EnumDocumentFreshnessStatus.FRESH == "fresh"
        assert EnumDocumentFreshnessStatus.STALE == "stale"
        assert EnumDocumentFreshnessStatus.CRITICAL == "critical"
        assert EnumDocumentFreshnessStatus.UNKNOWN == "unknown"

    def test_json_serialization(self):
        """Test JSON serialization."""
        data = {"status": EnumDocumentFreshnessStatus.STALE.value}
        json_str = json.dumps(data)
        assert '"status": "stale"' in json_str


class TestEnumDocumentType:
    """Test EnumDocumentType enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "DOCUMENT": "document",
            "CODE": "code",
            "CONFIG": "config",
            "DATA": "data",
        }

        for name, value in expected_values.items():
            doc_type = getattr(EnumDocumentType, name)
            assert doc_type.value == value

    def test_document_type_classification(self):
        """Test document type classification."""
        code_type = EnumDocumentType.CODE
        config_type = EnumDocumentType.CONFIG

        assert code_type != config_type
        assert code_type == "code"
        assert config_type == "config"

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class DocModel(BaseModel):
            doc_type: EnumDocumentType

        model = DocModel(doc_type=EnumDocumentType.CODE)
        assert model.doc_type == EnumDocumentType.CODE


class TestEnumRecommendationType:
    """Test EnumRecommendationType enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "UPDATE_REQUIRED": "update_required",
            "REVIEW_SUGGESTED": "review_suggested",
            "DEPRECATION_WARNING": "deprecation_warning",
            "OPTIMIZATION": "optimization",
        }

        for name, value in expected_values.items():
            rec_type = getattr(EnumRecommendationType, name)
            assert rec_type.value == value

    def test_recommendation_types(self):
        """Test different recommendation types."""
        assert EnumRecommendationType.UPDATE_REQUIRED == "update_required"
        assert EnumRecommendationType.DEPRECATION_WARNING == "deprecation_warning"

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        rec_types = list(EnumRecommendationType)
        assert len(rec_types) == 4


class TestEnumRecommendationPriority:
    """Test EnumRecommendationPriority enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "LOW": "low",
            "MEDIUM": "medium",
            "HIGH": "high",
            "CRITICAL": "critical",
        }

        for name, value in expected_values.items():
            priority = getattr(EnumRecommendationPriority, name)
            assert priority.value == value

    def test_priority_ordering(self):
        """Test that priorities can be compared."""
        priorities = list(EnumRecommendationPriority)
        assert len(priorities) == 4

        # Verify expected order
        assert priorities[0] == EnumRecommendationPriority.LOW
        assert priorities[-1] == EnumRecommendationPriority.CRITICAL

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class PriorityModel(BaseModel):
            priority: EnumRecommendationPriority

        model = PriorityModel(priority=EnumRecommendationPriority.HIGH)
        model_dict = model.model_dump()
        assert model_dict == {"priority": "high"}


class TestEnumEstimatedEffort:
    """Test EnumEstimatedEffort enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "MINUTES": "minutes",
            "HOURS": "hours",
            "DAYS": "days",
            "WEEKS": "weeks",
        }

        for name, value in expected_values.items():
            effort = getattr(EnumEstimatedEffort, name)
            assert effort.value == value

    def test_effort_levels(self):
        """Test effort level progression."""
        efforts = list(EnumEstimatedEffort)
        assert len(efforts) == 4

        # Verify order from shortest to longest
        assert efforts[0] == EnumEstimatedEffort.MINUTES
        assert efforts[-1] == EnumEstimatedEffort.WEEKS

    def test_string_equality(self):
        """Test that enum values equal their string representations."""
        assert EnumEstimatedEffort.MINUTES == "minutes"
        assert EnumEstimatedEffort.WEEKS == "weeks"


class TestEnumDependencyRelationship:
    """Test EnumDependencyRelationship enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "IMPORTS": "imports",
            "REFERENCES": "references",
            "INCLUDES": "includes",
            "DEPENDS_ON": "depends_on",
        }

        for name, value in expected_values.items():
            relationship = getattr(EnumDependencyRelationship, name)
            assert relationship.value == value

    def test_relationship_types(self):
        """Test different relationship types."""
        assert EnumDependencyRelationship.IMPORTS == "imports"
        assert EnumDependencyRelationship.DEPENDS_ON == "depends_on"

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class DependencyModel(BaseModel):
            relationship: EnumDependencyRelationship

        model = DependencyModel(relationship=EnumDependencyRelationship.IMPORTS)
        assert model.relationship == EnumDependencyRelationship.IMPORTS


class TestEnumOutputFormat:
    """Test EnumOutputFormat enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "JSON": "json",
            "MARKDOWN": "markdown",
            "HTML": "html",
        }

        for name, value in expected_values.items():
            output_format = getattr(EnumOutputFormat, name)
            assert output_format.value == value

    def test_format_types(self):
        """Test different output formats."""
        assert EnumOutputFormat.JSON == "json"
        assert EnumOutputFormat.MARKDOWN == "markdown"
        assert EnumOutputFormat.HTML == "html"

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        formats = list(EnumOutputFormat)
        assert len(formats) == 3


class TestDocumentFreshnessEnumsIntegration:
    """Test integration scenarios with multiple enums."""

    def test_comprehensive_document_analysis_model(self):
        """Test a comprehensive model using multiple freshness enums."""

        class DocumentAnalysisResult(BaseModel):
            action: EnumDocumentFreshnessActions
            status: EnumDocumentFreshnessStatus
            risk_level: EnumDocumentFreshnessRiskLevel
            doc_type: EnumDocumentType
            recommendation_type: EnumRecommendationType
            priority: EnumRecommendationPriority
            estimated_effort: EnumEstimatedEffort
            output_format: EnumOutputFormat

        # Create a comprehensive analysis result
        result = DocumentAnalysisResult(
            action=EnumDocumentFreshnessActions.AI_SEMANTIC_ANALYSIS,
            status=EnumDocumentFreshnessStatus.STALE,
            risk_level=EnumDocumentFreshnessRiskLevel.HIGH,
            doc_type=EnumDocumentType.CODE,
            recommendation_type=EnumRecommendationType.UPDATE_REQUIRED,
            priority=EnumRecommendationPriority.HIGH,
            estimated_effort=EnumEstimatedEffort.HOURS,
            output_format=EnumOutputFormat.JSON,
        )

        # Verify all fields
        assert result.action == EnumDocumentFreshnessActions.AI_SEMANTIC_ANALYSIS
        assert result.status == EnumDocumentFreshnessStatus.STALE
        assert result.risk_level == EnumDocumentFreshnessRiskLevel.HIGH
        assert result.doc_type == EnumDocumentType.CODE

        # Test serialization
        result_dict = result.model_dump()
        assert result_dict["action"] == "ai_semantic_analysis"
        assert result_dict["status"] == "stale"
        assert result_dict["risk_level"] == "high"

    def test_risk_and_priority_alignment(self):
        """Test that risk levels and priorities are semantically aligned."""
        # Both have LOW, MEDIUM, HIGH, CRITICAL
        risk_values = [r.value for r in EnumDocumentFreshnessRiskLevel]
        priority_values = [p.value for p in EnumRecommendationPriority]

        assert set(risk_values) == set(priority_values)

    def test_json_serialization_all_enums(self):
        """Test JSON serialization for all enums."""
        data = {
            "action": EnumDocumentFreshnessActions.MONITOR_FRESHNESS.value,
            "status": EnumDocumentFreshnessStatus.FRESH.value,
            "risk": EnumDocumentFreshnessRiskLevel.LOW.value,
            "type": EnumDocumentType.DOCUMENT.value,
            "recommendation": EnumRecommendationType.REVIEW_SUGGESTED.value,
            "priority": EnumRecommendationPriority.MEDIUM.value,
            "effort": EnumEstimatedEffort.MINUTES.value,
            "format": EnumOutputFormat.MARKDOWN.value,
        }

        json_str = json.dumps(data)
        loaded_data = json.loads(json_str)

        # Verify all values survived serialization
        assert loaded_data["action"] == "monitor_freshness"
        assert loaded_data["status"] == "fresh"
        assert loaded_data["risk"] == "low"

    def test_yaml_serialization_all_enums(self):
        """Test YAML serialization for all enums."""
        import yaml

        data = {
            "action": EnumDocumentFreshnessActions.GENERATE_AUDIT_REPORT.value,
            "status": EnumDocumentFreshnessStatus.CRITICAL.value,
            "risk": EnumDocumentFreshnessRiskLevel.CRITICAL.value,
        }

        yaml_str = yaml.dump(data, default_flow_style=False)
        loaded_data = yaml.safe_load(yaml_str)

        assert loaded_data["action"] == "generate_audit_report"
        assert loaded_data["status"] == "critical"
        assert loaded_data["risk"] == "critical"


class TestDocumentFreshnessEnumsEdgeCases:
    """Test edge cases across all freshness enums."""

    def test_all_enums_inherit_from_str(self):
        """Test that all enums inherit from str for JSON compatibility."""
        enums_to_test = [
            EnumDocumentFreshnessActions,
            EnumDocumentFreshnessRiskLevel,
            EnumDocumentFreshnessStatus,
            EnumDocumentType,
            EnumRecommendationType,
            EnumRecommendationPriority,
            EnumEstimatedEffort,
            EnumDependencyRelationship,
            EnumOutputFormat,
        ]

        for enum_class in enums_to_test:
            # Get first enum value
            first_value = next(iter(enum_class))
            # Should be comparable to string
            assert first_value == first_value.value

    def test_no_duplicate_values_in_any_enum(self):
        """Test that no enum has duplicate values."""
        enums_to_test = [
            EnumDocumentFreshnessActions,
            EnumDocumentFreshnessRiskLevel,
            EnumDocumentFreshnessStatus,
            EnumDocumentType,
            EnumRecommendationType,
            EnumRecommendationPriority,
            EnumEstimatedEffort,
            EnumDependencyRelationship,
            EnumOutputFormat,
        ]

        for enum_class in enums_to_test:
            values = [e.value for e in enum_class]
            assert len(values) == len(
                set(values)
            ), f"{enum_class.__name__} has duplicate values"

    def test_case_sensitivity_all_enums(self):
        """Test that all enum values use lowercase with underscores."""
        enums_to_test = [
            EnumDocumentFreshnessActions,
            EnumDocumentFreshnessRiskLevel,
            EnumDocumentFreshnessStatus,
            EnumDocumentType,
            EnumRecommendationType,
            EnumRecommendationPriority,
            EnumEstimatedEffort,
            EnumDependencyRelationship,
            EnumOutputFormat,
        ]

        for enum_class in enums_to_test:
            for enum_value in enum_class:
                # All values should be lowercase
                assert enum_value.value == enum_value.value.lower()
                # Should not contain spaces
                assert " " not in enum_value.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

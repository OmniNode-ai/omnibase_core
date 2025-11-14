"""Test EnumCollaborationDomain enum."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_collaboration_domain import EnumCollaborationDomain


class TestEnumCollaborationDomain:
    """Test EnumCollaborationDomain functionality."""

    def test_enum_inheritance(self):
        """Test enum inheritance."""
        assert issubclass(EnumCollaborationDomain, str)
        assert issubclass(EnumCollaborationDomain, Enum)

    def test_enum_values(self):
        """Test enum values."""
        assert EnumCollaborationDomain.FRONTEND_DEVELOPMENT == "frontend_development"
        assert EnumCollaborationDomain.BACKEND_DEVELOPMENT == "backend_development"
        assert EnumCollaborationDomain.INFRASTRUCTURE == "infrastructure"
        assert EnumCollaborationDomain.DATABASE == "database"
        assert EnumCollaborationDomain.TESTING == "testing"
        assert EnumCollaborationDomain.SECURITY_ANALYSIS == "security_analysis"
        assert (
            EnumCollaborationDomain.PERFORMANCE_OPTIMIZATION
            == "performance_optimization"
        )
        assert EnumCollaborationDomain.CODE_REVIEW == "code_review"

    def test_enum_string_behavior(self):
        """Test enum string behavior."""
        domain = EnumCollaborationDomain.FRONTEND_DEVELOPMENT
        assert isinstance(domain, str)
        assert domain == "frontend_development"
        assert len(domain) == 20
        assert domain.startswith("frontend")

    def test_enum_iteration(self):
        """Test enum iteration."""
        values = list(EnumCollaborationDomain)
        assert len(values) == 18
        assert EnumCollaborationDomain.FRONTEND_DEVELOPMENT in values
        assert EnumCollaborationDomain.RESOURCE_PLANNING in values

    def test_enum_membership(self):
        """Test enum membership."""
        assert "frontend_development" in EnumCollaborationDomain
        assert "testing" in EnumCollaborationDomain
        assert "invalid_domain" not in EnumCollaborationDomain

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumCollaborationDomain.FRONTEND_DEVELOPMENT == "frontend_development"
        assert EnumCollaborationDomain.FRONTEND_DEVELOPMENT != "backend_development"
        assert EnumCollaborationDomain.DATABASE < EnumCollaborationDomain.TESTING

    def test_enum_serialization(self):
        """Test enum serialization."""
        domain = EnumCollaborationDomain.SECURITY_ANALYSIS
        serialized = domain.value
        assert serialized == "security_analysis"
        import json

        json_str = json.dumps(domain)
        assert json_str == '"security_analysis"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        domain = EnumCollaborationDomain("testing")
        assert domain == EnumCollaborationDomain.TESTING

    def test_enum_invalid_value(self):
        """Test enum with invalid value."""
        with pytest.raises(ValueError):
            EnumCollaborationDomain("invalid_domain")

    def test_enum_all_values(self):
        """Test all enum values."""
        expected_values = [
            "frontend_development",
            "backend_development",
            "infrastructure",
            "database",
            "testing",
            "security_analysis",
            "performance_optimization",
            "code_review",
            "problem_diagnosis",
            "root_cause_analysis",
            "pattern_recognition",
            "requirements_analysis",
            "technical_documentation",
            "user_documentation",
            "api_documentation",
            "task_coordination",
            "progress_tracking",
            "resource_planning",
        ]
        actual_values = [e.value for e in EnumCollaborationDomain]
        assert set(actual_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test enum docstring."""
        assert EnumCollaborationDomain.__doc__ is not None
        assert "collaboration domains" in EnumCollaborationDomain.__doc__

    def test_development_domains(self):
        """Test development domain values."""
        dev_domains = [
            EnumCollaborationDomain.FRONTEND_DEVELOPMENT,
            EnumCollaborationDomain.BACKEND_DEVELOPMENT,
            EnumCollaborationDomain.INFRASTRUCTURE,
            EnumCollaborationDomain.DATABASE,
        ]

        for domain in dev_domains:
            assert isinstance(domain, str)
            assert (
                "_development" in domain.value
                or domain == EnumCollaborationDomain.INFRASTRUCTURE
                or domain == EnumCollaborationDomain.DATABASE
            )

    def test_quality_assurance_domains(self):
        """Test quality assurance domain values."""
        qa_domains = [
            EnumCollaborationDomain.TESTING,
            EnumCollaborationDomain.SECURITY_ANALYSIS,
            EnumCollaborationDomain.PERFORMANCE_OPTIMIZATION,
            EnumCollaborationDomain.CODE_REVIEW,
        ]

        for domain in qa_domains:
            assert isinstance(domain, str)
            assert domain.value in [
                "testing",
                "security_analysis",
                "performance_optimization",
                "code_review",
            ]

    def test_analysis_domains(self):
        """Test analysis domain values."""
        analysis_domains = [
            EnumCollaborationDomain.PROBLEM_DIAGNOSIS,
            EnumCollaborationDomain.ROOT_CAUSE_ANALYSIS,
            EnumCollaborationDomain.PATTERN_RECOGNITION,
            EnumCollaborationDomain.REQUIREMENTS_ANALYSIS,
        ]

        for domain in analysis_domains:
            assert isinstance(domain, str)
            assert (
                "_analysis" in domain.value
                or "diagnosis" in domain.value
                or "recognition" in domain.value
            )

    def test_documentation_domains(self):
        """Test documentation domain values."""
        doc_domains = [
            EnumCollaborationDomain.TECHNICAL_DOCUMENTATION,
            EnumCollaborationDomain.USER_DOCUMENTATION,
            EnumCollaborationDomain.API_DOCUMENTATION,
        ]

        for domain in doc_domains:
            assert isinstance(domain, str)
            assert "_documentation" in domain.value

    def test_project_management_domains(self):
        """Test project management domain values."""
        pm_domains = [
            EnumCollaborationDomain.TASK_COORDINATION,
            EnumCollaborationDomain.PROGRESS_TRACKING,
            EnumCollaborationDomain.RESOURCE_PLANNING,
        ]

        for domain in pm_domains:
            assert isinstance(domain, str)
            assert domain.value in [
                "task_coordination",
                "progress_tracking",
                "resource_planning",
            ]

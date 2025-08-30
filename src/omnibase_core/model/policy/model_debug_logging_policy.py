"""Pydantic model for ONEX Debug Logging Policy.

This model provides type-safe access to debug logging policy configuration
and ensures systematic incident investigation and documentation.
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional

import semver
from pydantic import BaseModel, Field, validator


class ModelDebugPhilosophy(BaseModel):
    """Model for debug logging philosophy."""

    systematic_investigation: bool = True
    structured_documentation: bool = True
    pattern_learning: bool = True
    proactive_prevention: bool = True
    rag_integration: bool = True
    historical_context: bool = True


class ModelLogStructure(BaseModel):
    """Model for debug log structure requirements."""

    title_format: str
    required_sections: List[str]
    optional_sections: List[str]


class ModelIssueClassification(BaseModel):
    """Model for issue classification system."""

    severity_levels: Dict[str, str]
    issue_types: Dict[str, str]


class ModelInvestigationProcess(BaseModel):
    """Model for systematic investigation methodology."""

    phase_1_detection: List[str]
    phase_2_context_gathering: List[str]
    phase_3_historical_analysis: List[str]
    phase_4_root_cause_analysis: List[str]
    phase_5_solution_development: List[str]
    phase_6_implementation: List[str]
    phase_7_learning_extraction: List[str]


class ModelRootCauseFramework(BaseModel):
    """Model for root cause analysis framework."""

    analysis_dimensions: Dict[str, str]
    questioning_techniques: Dict[str, str]
    evidence_collection: Dict[str, str]


class ModelSolutionStandards(BaseModel):
    """Model for solution documentation standards."""

    fix_categories: Dict[str, str]
    implementation_phases: Dict[str, str]
    validation_requirements: Dict[str, str]


class ModelRagIntegration(BaseModel):
    """Model for RAG service integration configuration."""

    query_patterns: Dict[str, str]
    context_enrichment: Dict[str, str]
    learning_extraction: Dict[str, str]


class ModelQualityRequirements(BaseModel):
    """Model for debug log quality standards."""

    completeness: Dict[str, bool]
    accuracy: Dict[str, bool]
    clarity: Dict[str, bool]
    actionability: Dict[str, bool]


class ModelIntegrations(BaseModel):
    """Model for external system integrations."""

    monitoring_systems: List[str]
    development_tools: List[str]
    communication_channels: List[str]
    knowledge_systems: List[str]


class ModelAutomation(BaseModel):
    """Model for automation triggers and processes."""

    auto_creation_triggers: List[str]
    context_auto_collection: List[str]
    rag_auto_queries: List[str]


class ModelTemplates(BaseModel):
    """Model for debug log templates."""

    issue_summary: Dict[str, str]
    root_cause_analysis: Dict[str, str]
    lessons_learned: Dict[str, str]


class ModelMetrics(BaseModel):
    """Model for debug logging performance metrics."""

    investigation_efficiency: Dict[str, str]
    quality_indicators: Dict[str, str]
    learning_metrics: Dict[str, str]


class ModelMaintenance(BaseModel):
    """Model for policy maintenance configuration."""

    review_schedule: str
    update_process: str
    version_control: bool
    backward_compatibility: str
    stakeholders: List[str]

    @validator("backward_compatibility")
    def validate_semver(cls, v):
        """Validate that backward_compatibility follows semantic versioning."""
        try:
            semver.VersionInfo.parse(v)
            return v
        except ValueError:
            raise ValueError(f"backward_compatibility must be valid semver: {v}")


class ModelDebugLoggingPolicy(BaseModel):
    """Complete model for ONEX Debug Logging Policy."""

    version: str = Field(
        ..., description="Policy version following semantic versioning"
    )
    schema_version: str = Field(
        ..., description="Schema version following semantic versioning"
    )

    philosophy: ModelDebugPhilosophy
    log_structure: ModelLogStructure
    issue_classification: ModelIssueClassification
    investigation_process: ModelInvestigationProcess
    root_cause_framework: ModelRootCauseFramework
    solution_standards: ModelSolutionStandards
    rag_integration: ModelRagIntegration
    quality_requirements: ModelQualityRequirements
    integrations: ModelIntegrations
    automation: ModelAutomation
    templates: ModelTemplates
    metrics: ModelMetrics
    maintenance: ModelMaintenance

    @validator("version", "schema_version")
    def validate_semver_versions(cls, v):
        """Validate that versions follow semantic versioning."""
        try:
            semver.VersionInfo.parse(v)
            return v
        except ValueError:
            raise ValueError(f"Version must be valid semver: {v}")

    @validator("log_structure")
    def validate_required_sections(cls, v):
        """Ensure all critical sections are included."""
        critical_sections = [
            "issue_summary",
            "root_cause_analysis",
            "impact_assessment",
            "fix_implementation",
            "lessons_learned",
        ]

        missing_sections = [
            section
            for section in critical_sections
            if section not in v.required_sections
        ]
        if missing_sections:
            raise ValueError(f"Missing critical sections: {missing_sections}")

        return v

    def get_severity_level(self, severity: str) -> Optional[str]:
        """Get description for a severity level."""
        return self.issue_classification.severity_levels.get(severity)

    def get_issue_type(self, issue_type: str) -> Optional[str]:
        """Get description for an issue type."""
        return self.issue_classification.issue_types.get(issue_type)

    def get_template(self, template_name: str) -> Optional[str]:
        """Get a template format string."""
        template_dict = getattr(self.templates, template_name, None)
        if template_dict and isinstance(template_dict, dict):
            return template_dict.get("format")
        return None

    def format_debug_title(
        self, issue_description: str, date: Optional[datetime] = None
    ) -> str:
        """Format a debug log title according to policy."""
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y_%m_%d")
        return self.log_structure.title_format.format(
            issue_description=issue_description, date_yyyy_mm_dd=date_str
        )

    def validate_log_completeness(self, sections: List[str]) -> Dict[str, bool]:
        """Validate that a debug log has all required sections."""
        validation_result = {
            "has_all_required": True,
            "missing_required": [],
            "has_optional": [],
            "missing_optional": [],
        }

        # Check required sections
        missing_required = [
            section
            for section in self.log_structure.required_sections
            if section not in sections
        ]
        if missing_required:
            validation_result["has_all_required"] = False
            validation_result["missing_required"] = missing_required

        # Check optional sections
        present_optional = [
            section
            for section in self.log_structure.optional_sections
            if section in sections
        ]
        missing_optional = [
            section
            for section in self.log_structure.optional_sections
            if section not in sections
        ]

        validation_result["has_optional"] = present_optional
        validation_result["missing_optional"] = missing_optional

        return validation_result

    def get_investigation_phases(self) -> List[str]:
        """Get ordered list of investigation phase names."""
        return [
            "phase_1_detection",
            "phase_2_context_gathering",
            "phase_3_historical_analysis",
            "phase_4_root_cause_analysis",
            "phase_5_solution_development",
            "phase_6_implementation",
            "phase_7_learning_extraction",
        ]

    def get_phase_activities(self, phase_name: str) -> List[str]:
        """Get activities for a specific investigation phase."""
        phase_data = getattr(self.investigation_process, phase_name, None)
        return phase_data if phase_data else []

    def should_auto_create(self, trigger: str) -> bool:
        """Check if a trigger should auto-create a debug log."""
        return trigger in self.automation.auto_creation_triggers

    def get_rag_query_pattern(self, query_type: str) -> Optional[str]:
        """Get RAG query pattern for a specific type."""
        return self.rag_integration.query_patterns.get(query_type)

    def is_compatible_with_version(self, other_version: str) -> bool:
        """Check if this policy version is compatible with another version."""
        try:
            current = semver.VersionInfo.parse(self.version)
            other = semver.VersionInfo.parse(other_version)
            backward_compat = semver.VersionInfo.parse(
                self.maintenance.backward_compatibility
            )

            # Compatible if other version is within backward compatibility range
            return other >= backward_compat and other.major == current.major
        except ValueError:
            return False


class ModelDebugEntry(BaseModel):
    """Model for individual debug log entries."""

    title: str
    date: datetime
    severity: Literal["critical", "high", "medium", "low"]
    issue_type: str
    status: Literal["investigating", "resolved", "monitoring", "closed"]

    # Core sections
    issue_summary: str
    root_cause_analysis: Optional[str] = None
    impact_assessment: Optional[str] = None
    fix_implementation: Optional[str] = None
    recommended_solutions: Optional[str] = None
    lessons_learned: Optional[str] = None
    action_items: Optional[List[str]] = None
    test_cases: Optional[str] = None

    # Optional sections
    timeline: Optional[str] = None
    stakeholder_communication: Optional[str] = None
    rollback_procedures: Optional[str] = None
    monitoring_setup: Optional[str] = None

    # Metadata
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    related_issues: Optional[List[str]] = None
    related_prs: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    def get_filename(self) -> str:
        """Generate filename for this debug log entry."""
        # Convert title to safe filename format
        safe_title = "".join(
            c for c in self.title if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        safe_title = safe_title.replace(" ", "_").lower()

        date_str = self.date.strftime("%Y_%m_%d")
        return f"debug_log_{date_str}_{safe_title}.md"

    def validate_completeness(self, policy: ModelDebugLoggingPolicy) -> Dict[str, bool]:
        """Validate this debug entry against policy requirements."""
        sections = []

        # Check which sections have content
        if self.issue_summary:
            sections.append("issue_summary")
        if self.root_cause_analysis:
            sections.append("root_cause_analysis")
        if self.impact_assessment:
            sections.append("impact_assessment")
        if self.fix_implementation:
            sections.append("fix_implementation")
        if self.recommended_solutions:
            sections.append("recommended_solutions")
        if self.lessons_learned:
            sections.append("lessons_learned")
        if self.action_items:
            sections.append("action_items")
        if self.test_cases:
            sections.append("test_cases")

        return policy.validate_log_completeness(sections)


class ModelDebugLoggingPolicyWrapper(BaseModel):
    """Wrapper model that matches the YAML structure."""

    debug_logging_policy: ModelDebugLoggingPolicy

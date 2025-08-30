"""
Typing violation models for the OmniMemory typing corrector system.

These models define structures for detecting, analyzing, and correcting
typing violations in generated code, particularly focusing on eliminating
Dict[str, Any] and enforcing strong typing standards.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EnumTypingViolationType(str, Enum):
    """Types of typing violations that can be detected."""

    DICT_STR_ANY = "dict_str_any"
    UNTYPED_RETURN = "untyped_return"
    UNTYPED_PARAMETER = "untyped_parameter"
    MISSING_TYPE_HINT = "missing_type_hint"
    GENERIC_ANY_USAGE = "generic_any_usage"
    IMPLICIT_OPTIONAL = "implicit_optional"
    WEAK_TYPING = "weak_typing"
    PROTOCOL_VIOLATION = "protocol_violation"


class EnumTypingViolationSeverity(str, Enum):
    """Severity levels for typing violations."""

    CRITICAL = "critical"  # Must be fixed before generation
    HIGH = "high"  # Should be fixed
    MEDIUM = "medium"  # Recommended to fix
    LOW = "low"  # Optional improvement


class EnumTypingCorrectionStrategy(str, Enum):
    """Strategies for correcting typing violations."""

    REPLACE_WITH_MODEL = "replace_with_model"
    ADD_TYPE_ANNOTATION = "add_type_annotation"
    GENERATE_PROTOCOL = "generate_protocol"
    USE_GENERIC = "use_generic"
    CONVERT_TO_UNION = "convert_to_union"
    ADD_TYPE_IMPORT = "add_type_import"


class ModelTypingViolation(BaseModel):
    """Model for a detected typing violation."""

    violation_id: str = Field(description="Unique identifier for this violation")
    violation_type: EnumTypingViolationType = Field(
        description="Type of typing violation detected"
    )
    severity: EnumTypingViolationSeverity = Field(
        description="Severity level of this violation"
    )

    # Location information
    file_path: Optional[str] = Field(
        default=None, description="File path where violation was found"
    )
    line_number: Optional[int] = Field(
        default=None, description="Line number where violation occurs"
    )
    column_number: Optional[int] = Field(
        default=None, description="Column number where violation starts"
    )

    # Violation details
    original_code: str = Field(description="Original code that contains the violation")
    problematic_pattern: str = Field(
        description="Specific pattern that violates typing standards"
    )
    context: str = Field(description="Surrounding code context for the violation")

    # Detection metadata
    detected_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this violation was detected"
    )
    detection_method: str = Field(
        description="Method used to detect this violation (ast, regex, etc.)"
    )

    # Suggested correction
    suggested_correction: Optional[str] = Field(
        default=None, description="Suggested corrected code"
    )
    correction_strategy: Optional[EnumTypingCorrectionStrategy] = Field(
        default=None, description="Strategy used for correction"
    )

    # Additional context
    function_name: Optional[str] = Field(
        default=None, description="Name of function containing the violation"
    )
    class_name: Optional[str] = Field(
        default=None, description="Name of class containing the violation"
    )
    variable_name: Optional[str] = Field(
        default=None, description="Name of variable with typing violation"
    )


class ModelTypingCorrection(BaseModel):
    """Model for a typing correction action."""

    correction_id: str = Field(description="Unique identifier for this correction")
    violation_id: str = Field(description="ID of the violation being corrected")

    # Correction details
    strategy: EnumTypingCorrectionStrategy = Field(
        description="Strategy used for this correction"
    )
    original_code: str = Field(description="Original code before correction")
    corrected_code: str = Field(description="Code after applying correction")

    # Additional changes required
    required_imports: List[str] = Field(
        default_factory=list, description="Import statements that need to be added"
    )
    generated_models: List[str] = Field(
        default_factory=list, description="New model classes that need to be generated"
    )

    # Correction metadata
    applied: bool = Field(
        default=False, description="Whether this correction has been applied"
    )
    confidence_score: float = Field(
        default=1.0, description="Confidence in this correction (0.0-1.0)"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this correction was created"
    )
    applied_at: Optional[datetime] = Field(
        default=None, description="When this correction was applied"
    )

    # Validation
    validation_passed: Optional[bool] = Field(
        default=None, description="Whether corrected code passed validation"
    )
    validation_errors: List[str] = Field(
        default_factory=list, description="Validation errors if validation failed"
    )


class ModelTypingAnalysisResult(BaseModel):
    """Model for the result of typing analysis on code."""

    analysis_id: str = Field(description="Unique identifier for this analysis")

    # Input information
    code_content: str = Field(description="Code that was analyzed")
    file_path: Optional[str] = Field(
        default=None, description="Path of file that was analyzed"
    )

    # Analysis results
    violations_found: int = Field(description="Total number of violations detected")
    violations: List[ModelTypingViolation] = Field(
        default_factory=list, description="List of all detected violations"
    )

    # Correction proposals
    corrections_generated: int = Field(description="Number of corrections generated")
    corrections: List[ModelTypingCorrection] = Field(
        default_factory=list, description="List of proposed corrections"
    )

    # Analysis metadata
    analysis_duration_ms: float = Field(
        description="Time taken for analysis in milliseconds"
    )
    analyzer_version: str = Field(
        default="1.0.0", description="Version of the typing analyzer used"
    )

    # Quality metrics
    critical_violations: int = Field(
        description="Number of critical severity violations"
    )
    high_violations: int = Field(description="Number of high severity violations")
    correctability_score: float = Field(
        description="Score indicating how easily violations can be corrected"
    )

    # Timestamps
    analyzed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this analysis was performed"
    )


class ModelTypingCorrectionBatch(BaseModel):
    """Model for a batch of typing corrections applied together."""

    batch_id: str = Field(description="Unique identifier for this correction batch")

    # Batch contents
    corrections: List[ModelTypingCorrection] = Field(
        description="List of corrections in this batch"
    )
    total_corrections: int = Field(description="Total number of corrections in batch")

    # Batch execution
    applied_successfully: int = Field(
        default=0, description="Number of corrections applied successfully"
    )
    failed_corrections: int = Field(
        default=0, description="Number of corrections that failed"
    )

    # Generated artifacts
    generated_files: List[str] = Field(
        default_factory=list, description="New files generated during correction"
    )
    modified_files: List[str] = Field(
        default_factory=list, description="Existing files that were modified"
    )

    # Batch metadata
    batch_execution_time_ms: float = Field(description="Total time for batch execution")

    # Quality assurance
    validation_passed: bool = Field(
        description="Whether all corrections passed validation"
    )
    syntax_valid: bool = Field(description="Whether resulting code has valid syntax")
    imports_resolved: bool = Field(
        description="Whether all required imports were resolved"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this batch was created"
    )
    executed_at: Optional[datetime] = Field(
        default=None, description="When this batch was executed"
    )


class ModelTypingRule(BaseModel):
    """Model for a typing enforcement rule."""

    rule_id: str = Field(description="Unique identifier for this typing rule")
    name: str = Field(description="Human-readable name for the rule")
    description: str = Field(description="Description of what this rule enforces")

    # Rule pattern
    violation_pattern: str = Field(description="Pattern that identifies violations")
    correction_template: str = Field(description="Template for generating corrections")

    # Rule configuration
    severity: EnumTypingViolationSeverity = Field(
        description="Severity level for violations of this rule"
    )
    strategy: EnumTypingCorrectionStrategy = Field(
        description="Default correction strategy for this rule"
    )

    enabled: bool = Field(
        default=True, description="Whether this rule is currently active"
    )

    # Rule effectiveness
    violations_detected: int = Field(
        default=0, description="Total violations detected by this rule"
    )
    corrections_successful: int = Field(
        default=0, description="Successful corrections made by this rule"
    )
    success_rate: float = Field(
        default=0.0, description="Success rate for this rule's corrections"
    )

    # Rule metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this rule was created"
    )
    last_triggered: Optional[datetime] = Field(
        default=None, description="Last time this rule detected a violation"
    )

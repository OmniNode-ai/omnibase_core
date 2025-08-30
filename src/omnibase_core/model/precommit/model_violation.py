"""Model for pre-commit violations."""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_severity import EnumSeverity


class ModelViolation(BaseModel):
    """Model representing a single pre-commit violation."""

    file_path: str = Field(..., description="Path to file with violation")
    line_number: int = Field(..., description="Line number where violation occurs")
    category: str = Field(..., description="Category of violation")
    severity: EnumSeverity = Field(..., description="Severity level of violation")
    description: str = Field(..., description="Human-readable description of violation")
    matched_text: str = Field(..., description="Text that matched the pattern")
    full_line: str = Field(..., description="Full line containing violation")
    pattern: str = Field(..., description="Pattern that was matched")

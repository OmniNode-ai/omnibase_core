from pydantic import BaseModel

from omnibase_core.enums.enum_issue_type import EnumIssueTypeEnum
from omnibase_core.enums.enum_log_level import EnumLogLevel


class ModelValidationIssue(BaseModel):
    """Represents a template validation issue with proper typing"""

    file_path: str
    line_number: int
    issue_type: EnumIssueTypeEnum
    description: str
    severity: EnumLogLevel
    suggested_fix: str = ""

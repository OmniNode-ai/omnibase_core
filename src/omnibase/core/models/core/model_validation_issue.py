from pydantic import BaseModel

from omnibase.enums.enum_issue_type import EnumIssueTypeEnum
from omnibase.enums.enum_log_level import SeverityLevelEnum


class ModelValidationIssue(BaseModel):
    """Represents a template validation issue with proper typing"""

    file_path: str
    line_number: int
    issue_type: EnumIssueTypeEnum
    description: str
    severity: SeverityLevelEnum
    suggested_fix: str = ""

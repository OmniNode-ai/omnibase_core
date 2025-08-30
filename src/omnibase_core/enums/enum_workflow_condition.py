from enum import Enum


class EnumWorkflowCondition(Enum):
    """Enumeration of Workflow node execution conditions."""

    ALWAYS = "always"
    SUCCESS = "success"
    FAILURE = "failure"
    COMPLETION = "completion"
    MANUAL = "manual"

from enum import Enum


class EnumIssueType(str, Enum):
    """Template validation issue types for node generation"""

    TEMPLATE_ARTIFACT = "template_artifact"
    INCORRECT_NODE_NAME = "incorrect_node_name"
    PARSE_ERROR = "parse_error"
    TODO_FOUND = "todo_found"
    INCORRECT_CLASS_NAME = "incorrect_class_name"
    INCORRECT_ENUM_NAME = "incorrect_enum_name"
    INCORRECT_MODEL_NAME = "incorrect_model_name"
    INCORRECT_TITLE = "incorrect_title"
    MISSING_DIRECTORY = "missing_directory"

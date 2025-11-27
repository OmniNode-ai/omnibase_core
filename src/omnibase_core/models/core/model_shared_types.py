# This file imports commonly used models for re-export

from omnibase_core.models.core.model_function_tool import ModelFunctionTool
from omnibase_core.models.core.model_tool_collection import ModelToolCollection

# Re-export for current standards
__all__ = [
    "ModelFunctionTool",
    "ModelToolCollection",
]

"""
Logging configuration model.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_log_format import EnumLogFormat

from .model_loggingconfig import ModelLoggingConfig

# Compatibility alias

__all__ = [
    "EnumLogFormat",
    "ModelLogFormat",
    "ModelLoggingConfig",
]

ModelLogFormat = EnumLogFormat

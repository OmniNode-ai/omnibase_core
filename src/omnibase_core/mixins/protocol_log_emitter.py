from __future__ import annotations

"""
Protocol for log emission.
"""


from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from omnibase_core.mixins.model_mixin_log_data import ModelMixinLogData

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel


class LogEmitter(Protocol):
    """Protocol for log emission."""

    def emit_log_event(
        self,
        level: LogLevel,
        message: str,
        data: "ModelMixinLogData",
    ) -> None: ...

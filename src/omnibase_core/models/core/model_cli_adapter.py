"""
Base CLI adapter class that provides consistent exit code handling.

All CLI adapters should inherit from this class or implement similar
exit code mapping functionality.
"""

from __future__ import annotations

import sys

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_codes import get_exit_code_for_status
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_bootstrap import emit_log_event_sync


class ModelCLIAdapter:
    """
    Base CLI adapter class that provides consistent exit code handling.

    All CLI adapters should inherit from this class or implement similar
    exit code mapping functionality.
    """

    @staticmethod
    def exit_with_status(status: EnumOnexStatus, message: str = "") -> None:
        """
        Exit the CLI with the appropriate exit code for the given status.

        Args:
            status: The EnumOnexStatus to map to an exit code
            message: Optional message to print before exiting
        """
        exit_code = get_exit_code_for_status(status)

        if message:
            if status in (EnumOnexStatus.ERROR, EnumOnexStatus.UNKNOWN):
                emit_log_event_sync(
                    level=LogLevel.ERROR,
                    message=message,
                    event_type="cli_exit_error",
                    data={"status": status.value, "exit_code": exit_code},
                )
            elif status == EnumOnexStatus.WARNING:
                emit_log_event_sync(
                    level=LogLevel.WARNING,
                    message=message,
                    event_type="cli_exit_warning",
                    data={"status": status.value, "exit_code": exit_code},
                )
            else:
                emit_log_event_sync(
                    level=LogLevel.INFO,
                    message=message,
                    event_type="cli_exit_info",
                    data={"status": status.value, "exit_code": exit_code},
                )

        sys.exit(exit_code)

    @staticmethod
    def exit_with_error(error: ModelOnexError) -> None:
        """
        Exit the CLI with the appropriate exit code for the given error.

        Args:
            error: The ModelOnexError to handle
        """
        exit_code = error.get_exit_code()
        emit_log_event_sync(
            level=LogLevel.ERROR,
            message=str(error),
            event_type="cli_exit_with_error",
            correlation_id=error.correlation_id,
            data={
                "error_code": str(error.error_code) if error.error_code else None,
                "exit_code": exit_code,
                "context": error.context,
            },
        )
        sys.exit(exit_code)


# Export for use
__all__ = [
    "ModelCLIAdapter",
]

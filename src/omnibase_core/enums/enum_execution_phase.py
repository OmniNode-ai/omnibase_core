from __future__ import annotations

"""
Execution Phase Enumeration.

Defines the various phases of execution for CLI commands and operations.
"""


from enum import Enum, unique


@unique
class EnumExecutionPhase(str, Enum):
    """
    Execution phase enumeration.

    Represents the different phases during command or operation execution.
    """

    # Initial phases
    INITIALIZATION = "initialization"
    VALIDATION = "validation"
    PREPARATION = "preparation"

    # Core execution phases
    PARSING = "parsing"
    PROCESSING = "processing"
    EXECUTION = "execution"
    COMPILATION = "compilation"

    # IO phases
    READING_INPUT = "reading_input"
    WRITING_OUTPUT = "writing_output"
    FILE_OPERATIONS = "file_operations"

    # Network phases
    CONNECTING = "connecting"
    DOWNLOADING = "downloading"
    UPLOADING = "uploading"

    # Analysis phases
    ANALYZING = "analyzing"
    SCANNING = "scanning"
    VALIDATING = "validating"

    # Finalization phases
    CLEANUP = "cleanup"
    FINALIZATION = "finalization"
    TEARDOWN = "teardown"

    # Error handling phases
    ERROR_HANDLING = "error_handling"
    RECOVERY = "recovery"
    ROLLBACK = "rollback"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.value.replace("_", " ").title()

    @classmethod
    def get_all_phases(cls) -> list[EnumExecutionPhase]:
        """Get all execution phases."""
        return list(cls)

    @classmethod
    def get_core_phases(cls) -> list[EnumExecutionPhase]:
        """Get core execution phases."""
        return [
            cls.PARSING,
            cls.PROCESSING,
            cls.EXECUTION,
            cls.COMPILATION,
        ]

    @classmethod
    def get_io_phases(cls) -> list[EnumExecutionPhase]:
        """Get IO-related phases."""
        return [
            cls.READING_INPUT,
            cls.WRITING_OUTPUT,
            cls.FILE_OPERATIONS,
        ]

    @classmethod
    def get_network_phases(cls) -> list[EnumExecutionPhase]:
        """Get network-related phases."""
        return [
            cls.CONNECTING,
            cls.DOWNLOADING,
            cls.UPLOADING,
        ]


# Export for use
__all__ = ["EnumExecutionPhase"]

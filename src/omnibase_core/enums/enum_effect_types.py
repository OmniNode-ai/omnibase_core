"""
Effect-related enumerations for NodeEffect operations.

Defines types of side effects and transaction states for managing
external interactions and resilience patterns.
"""

from enum import Enum, unique
from typing import Never, NoReturn

__all__ = [
    "EnumEffectType",
    "EnumTransactionState",
]


@unique
class EnumEffectType(Enum):
    """Types of side effects that can be managed."""

    FILE_OPERATION = "file_operation"
    DATABASE_OPERATION = "database_operation"
    API_CALL = "api_call"
    EVENT_EMISSION = "event_emission"
    DIRECTORY_OPERATION = "directory_operation"
    TICKET_STORAGE = "ticket_storage"
    METRICS_COLLECTION = "metrics_collection"

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling of all enum values in match statements.

        This method enables static type checkers to verify that all enum values
        are handled in match/case statements. If a case is missing, mypy will
        report an error at the call site.

        Usage:
            match effect_type:
                case EnumEffectType.FILE_OPERATION:
                    handle_file()
                case EnumEffectType.DATABASE_OPERATION:
                    handle_db()
                case EnumEffectType.API_CALL:
                    handle_api()
                case EnumEffectType.EVENT_EMISSION:
                    handle_event()
                case EnumEffectType.DIRECTORY_OPERATION:
                    handle_directory()
                case EnumEffectType.TICKET_STORAGE:
                    handle_ticket()
                case EnumEffectType.METRICS_COLLECTION:
                    handle_metrics()
                case _ as unreachable:
                    EnumEffectType.assert_exhaustive(unreachable)

        Args:
            value: The unhandled enum value (typed as Never for exhaustiveness).

        Raises:
            AssertionError: Always raised if this code path is reached at runtime.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


@unique
class EnumTransactionState(Enum):
    """Transaction state tracking."""

    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling of all enum values in match statements.

        This method enables static type checkers to verify that all enum values
        are handled in match/case statements. If a case is missing, mypy will
        report an error at the call site.

        Usage:
            match transaction_state:
                case EnumTransactionState.PENDING:
                    handle_pending()
                case EnumTransactionState.ACTIVE:
                    handle_active()
                case EnumTransactionState.COMMITTED:
                    handle_committed()
                case EnumTransactionState.ROLLED_BACK:
                    handle_rolled_back()
                case EnumTransactionState.FAILED:
                    handle_failed()
                case _ as unreachable:
                    EnumTransactionState.assert_exhaustive(unreachable)

        Args:
            value: The unhandled enum value (typed as Never for exhaustiveness).

        Raises:
            AssertionError: Always raised if this code path is reached at runtime.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")

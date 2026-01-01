"""
Simple Fallback Logger.

A simple fallback logger that just prints to stdout/stderr,
used when the full logging infrastructure is not available
during bootstrap or circular dependency scenarios.
"""

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel


class _SimpleFallbackLogger:
    """Simple fallback logger that just prints to stdout."""

    def emit(self, level: LogLevel, message: str, correlation_id: str | None) -> None:
        """Emit log message to stdout."""
        import sys

        # ERROR and CRITICAL levels go to stderr, others to stdout
        is_error = level in (LogLevel.ERROR, LogLevel.CRITICAL, LogLevel.FATAL)
        # print-ok: fallback logger intentionally uses print when logging infra unavailable
        print(
            f"[{level.name}] {correlation_id}: {message}",
            file=sys.stderr if is_error else sys.stdout,
        )

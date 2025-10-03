"""
Omnibase Core - Exception Definitions

Exception classes for ONEX architecture error handling.

All exception implementations are now located in omnibase_core.errors.
This module re-exports for backward compatibility.
"""

from omnibase_core.errors.error_codes import OnexError

__all__: list[str] = ["OnexError"]

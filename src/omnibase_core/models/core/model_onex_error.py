"""
This file is deprecated and should not be used.

ModelOnexError is now defined in omnibase_core.errors.error_codes as the canonical
Exception class. Import from there instead:

    from omnibase_core.errors.error_codes import ModelOnexError

This file is kept temporarily for backwards compatibility but will be removed.
"""

# Re-export ModelOnexError from canonical location
from omnibase_core.errors.error_codes import ModelOnexError  # noqa: F401

__all__ = ["ModelOnexError"]

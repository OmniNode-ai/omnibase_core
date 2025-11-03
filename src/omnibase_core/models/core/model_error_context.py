"""
Model for representing error context with proper type safety.

This model replaces dictionary usage in error contexts by providing
a structured representation of error context data.

Note: The actual ModelErrorContext class is defined in omnibase_core.models.common.model_error_context.
"""

from omnibase_core.models.common.model_error_context import ModelErrorContext

__all__ = ["ModelErrorContext"]

"""Core models import compatibility module."""

# Re-export from the new location
import warnings

from omnibase_core.models.core import *  # noqa: F403, F401

warnings.warn(
    "Importing from omnibase_core.model.core is deprecated. Use omnibase_core.models.core instead.",
    DeprecationWarning,
    stacklevel=2,
)

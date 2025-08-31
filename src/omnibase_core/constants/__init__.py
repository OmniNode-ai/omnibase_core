"""
Constants module for omnibase_core.

This module re-exports constants from the core.constants location
and provides additional constants modules to maintain backward compatibility.
"""

# Import specific modules for submodule access
from omnibase_core.core.constants import contract_constants, event_types

# Re-export all constants from their actual locations
from omnibase_core.core.constants.contract_constants import *  # noqa: F401,F403
from omnibase_core.core.constants.event_types import *  # noqa: F401,F403

# Import local constants modules
from . import constants_contract_fields

# Make them available as submodules
__all__ = ["contract_constants", "event_types", "constants_contract_fields"]

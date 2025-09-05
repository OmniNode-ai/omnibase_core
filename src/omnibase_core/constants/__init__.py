"""
Constants module for omnibase_core.

This module re-exports constants from the core.constants location
and provides additional constants modules to maintain backward compatibility.
"""

# Import specific modules for submodule access - no star imports
from omnibase_core.core.constants import contract_constants, event_types

# Import local constants modules
from . import constants_contract_fields

# Make them available as submodules without star imports to avoid circular dependencies
__all__ = ["constants_contract_fields", "contract_constants", "event_types"]

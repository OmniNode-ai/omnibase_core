"""Core models for OmniBase - Core domain models only.

This module contains only core domain models to prevent circular dependencies.
Other domains should import from their respective modules directly.
"""

# Configuration base classes
from .model_configuration_base import ModelConfigurationBase

# Generic container pattern
from .model_container import ModelContainer
from .model_custom_fields_accessor import ModelCustomFieldsAccessor

# Custom properties pattern
from .model_custom_properties import ModelCustomProperties
from .model_environment_accessor import ModelEnvironmentAccessor

# Field accessor patterns
from .model_field_accessor import ModelFieldAccessor

# Generic collection pattern
from .model_generic_collection import ModelGenericCollection
from .model_generic_collection_summary import ModelGenericCollectionSummary
from .model_result_accessor import ModelResultAccessor
from .model_typed_accessor import ModelTypedAccessor
from .model_typed_configuration import ModelTypedConfiguration

# Generic factory pattern
try:
    from .model_capability_factory import ModelCapabilityFactory
    from .model_generic_factory import ModelGenericFactory
    from .model_result_factory import ModelResultFactory
    from .model_validation_error_factory import ModelValidationErrorFactory

    _FACTORY_AVAILABLE = True
except ImportError:
    # Graceful degradation if circular imports prevent loading
    _FACTORY_AVAILABLE = False

__all__ = [
    # Configuration base classes
    "ModelConfigurationBase",
    "ModelTypedConfiguration",
    # Custom properties pattern
    "ModelCustomProperties",
    # Generic container pattern
    "ModelContainer",
    # Field accessor patterns
    "ModelFieldAccessor",
    "ModelTypedAccessor",
    "ModelEnvironmentAccessor",
    "ModelResultAccessor",
    "ModelCustomFieldsAccessor",
    # Generic collection pattern
    "ModelGenericCollection",
    "ModelGenericCollectionSummary",
    # Factory patterns (with graceful degradation)
    "ModelCapabilityFactory",
    "ModelGenericFactory",
    "ModelResultFactory",
    "ModelValidationErrorFactory",
]

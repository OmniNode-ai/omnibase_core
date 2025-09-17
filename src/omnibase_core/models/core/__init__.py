"""
Core Domain Models - ONEX Framework

This module contains fundamental models that form the foundation of the ONEX architecture.
All models follow proper typing standards using ModelSemVer for versions and strong typing patterns.

Key Models:
- ModelSemVer: Semantic versioning with proper validation
- ModelNodeBase: Foundation for ONEX node implementations
- ModelBaseError, ModelBaseResult, ModelBaseState: Base classes for consistent patterns
- Action models: Action processing and validation
- Contract models: Contract management and validation
- Event models: Event handling and envelopes
- Metadata models: Structured metadata handling

All models in this domain MUST:
- Start with "model_" prefix
- Use ModelSemVer for version fields (never str)
- Follow ONEX type safety patterns
- Maintain proper validation and constraints
"""

# Action processing models
from .model_action_base import ModelActionBase
from .model_action_payload_base import ModelActionPayloadBase
from .model_base_error import ModelBaseError
from .model_base_result import ModelBaseResult
from .model_base_state import ModelBaseInputState, ModelBaseOutputState
from .model_generic_metadata import ModelGenericMetadata

# Configuration and metadata
from .model_generic_yaml import ModelGenericYaml
from .model_metadata_base import ModelMetadataBase

# Node and base models
from .model_node_base import ModelNodeBase
from .model_onex_base_state import ModelOnexBaseState
from .model_onex_envelope import ModelOnexEnvelope

# Core ONEX models for system integration
from .model_onex_error import ModelOnexError
from .model_onex_event import ModelOnexEvent
from .model_onex_result import ModelOnexResult

# Fundamental models - REQUIRED for all other models
from .model_semver import ModelSemVer, SemVerField

# Import subcontracts
from .subcontracts import *

__all__ = [
    # Fundamental types (REQUIRED)
    "ModelSemVer",
    "SemVerField",
    # Base classes for inheritance
    "ModelNodeBase",
    "ModelBaseError",
    "ModelBaseResult",
    "ModelBaseInputState",
    "ModelBaseOutputState",
    "ModelOnexBaseState",
    # Action processing
    "ModelActionBase",
    "ModelActionPayloadBase",
    # Core ONEX integration
    "ModelOnexError",
    "ModelOnexEvent",
    "ModelOnexEnvelope",
    "ModelOnexResult",
    # Configuration and metadata
    "ModelGenericYaml",
    "ModelMetadataBase",
    "ModelGenericMetadata",
]

"""
Contracts Domain Models - ONEX Framework

This module contains contract-related models for the ONEX architecture.
Contracts define the interface specifications and behavioral contracts for nodes.

Key Models:
- ModelContract: Node contract specification
- State Contract models: Input/output state contracts
- Action Contract models: Action-specific contracts
- IO Contract models: Input/output interface contracts
- Signature Contract models: Method signature contracts

All models in this domain MUST:
- Start with "model_" prefix
- Use ModelSemVer for version fields (never str)
- Follow ONEX type safety patterns
- Maintain proper validation and constraints
"""

# Core contract models
from .model_contract import ModelContract
from .model_contract_action import ModelContractAction
from .model_contract_cache import ModelContractCache
from .model_contract_content import ModelContractContent
from .model_contract_data import ModelContractData
from .model_contract_definitions import ModelContractDefinitions
from .model_contract_dependency import ModelContractDependency
from .model_contract_loader import ModelContractLoader
from .model_contract_reference import ModelContractReference
from .model_generic_contract import ModelGenericContract
from .model_hub_contract_config import ModelHubContractConfig
from .model_introspection_contract_info import ModelIntrospectionContractInfo
from .model_io_contract import ModelIOContract
from .model_signature_contract import ModelSignatureContract
from .model_state_contract import ModelStateContract
from .model_state_contract_block import ModelStateContractBlock
from .model_subcontract_reference import ModelSubcontractReference

# Import subcontracts
from .subcontracts import *

__all__ = [
    # Core contract models
    "ModelContract",
    "ModelContractAction",
    "ModelContractCache",
    "ModelContractContent",
    "ModelContractData",
    "ModelContractDefinitions",
    "ModelContractDependency",
    "ModelContractLoader",
    "ModelContractReference",
    "ModelGenericContract",
    "ModelHubContractConfig",
    "ModelIntrospectionContractInfo",
    "ModelIOContract",
    "ModelSignatureContract",
    "ModelStateContract",
    "ModelStateContractBlock",
    "ModelSubcontractReference",
]
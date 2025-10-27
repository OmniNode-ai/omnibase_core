"""
Validation error models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from .model_validate_message import ModelValidateMessage

# Import separated models
from .model_validate_message_context import ModelValidateMessageContext
from .model_validate_result import ModelValidateResult

# Compatibility aliases
ValidateMessageModelContext = ModelValidateMessageContext
ValidateMessageModel = ModelValidateMessage
ValidateResultModel = ModelValidateResult

# Re-export for current standards
__all__ = [
    "ModelValidateMessage",
    "ModelValidateMessageContext",
    "ModelValidateResult",
    "ValidateMessageModel",
    "ValidateMessageModelContext",
    "ValidateResultModel",
]

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.102429'
# description: Stamped by ToolPython
# entrypoint: python://model_validate_error
# hash: 7a7f65824ae092693311aeb9b9d3342dfbbd3dbafbf7c31fdfddb74eb5a97a2e
# last_modified_at: '2025-05-29T14:13:58.963573+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_validate_error.py
# namespace: python://omnibase.model.model_validate_error
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 120a665f-4735-4e7f-9bb9-0ecd4afa33ec
# version: 1.0.0
# === /OmniNode:Metadata ===

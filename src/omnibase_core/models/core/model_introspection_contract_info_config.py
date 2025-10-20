#!/usr/bin/env python3
"""
Introspection Contract Info Configuration - ONEX Standards Compliant.

Strongly-typed configuration class for introspection contract info.
"""

from omnibase_core.models.core.model_introspection_contract_info import (
    ModelIntrospectionContractInfo,
)


class ModelConfig:
    """Pydantic model configuration for ONEX compliance."""

    json_schema_extra = {
        "example": {
            "contract_version": {
                "major": 1,
                "minor": 0,
                "patch": 0,
                "prerelease": None,
                "build": None,
            },
            "has_definitions": True,
            "definition_count": 5,
            "contract_path": "/path/to/contract.yaml",
        },
    }

#!/usr/bin/env python3
"""
Introspection Contract Info Configuration.

Strongly-typed configuration class for introspection contract info.
"""


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

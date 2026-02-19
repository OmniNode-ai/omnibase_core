# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelIntrospectionValidation configuration.
"""


class ModelIntrospectionValidationConfig:
    json_schema_extra = {
        "example": {
            "is_modern": True,
            "has_modern_patterns": True,
            "cli_discoverable": True,
            "passes_standards": True,
        },
    }

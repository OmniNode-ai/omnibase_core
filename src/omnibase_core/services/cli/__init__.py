# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI services for the registry-driven dynamic CLI system.

Provides schema-driven argument parsing and dynamic command dispatch.

Import directly from the specific module per OMN-1071 policy:

    from omnibase_core.services.cli.service_schema_argument_parser import ServiceSchemaArgumentParser
    from omnibase_core.services.cli.service_command_dispatcher import ServiceCommandDispatcher

.. versionadded:: 0.19.0  (OMN-2553)
"""

# No imports at module level to avoid circular import issues.
# Import directly from the specific service module as documented above.

__all__: list[str] = []

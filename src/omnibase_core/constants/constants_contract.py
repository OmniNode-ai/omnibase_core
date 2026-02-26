# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Constants for ONEX contract file names and paths.

Single source of truth for contract-related filename constants
to avoid magic strings scattered across the codebase.

See Also:
    - constants_contract_fields.py: Contract field name constants
    - OMN-1533: contract.yaml startup validation
"""

# env-var-ok: constant definitions for contract filenames, not environment variables

# Standard ONEX contract filename used by all nodes
CONTRACT_FILENAME: str = "contract.yaml"

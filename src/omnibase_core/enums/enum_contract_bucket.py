# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract bucket enum for corpus path classification (OMN-9758, parent OMN-9757).

Classifies the role a contract YAML file plays in the corpus before
validation. Distinct from ``EnumNodeType`` (which discriminates node
implementation kind) — ``EnumContractBucket`` discriminates the file-path
classification bucket used by the corpus classification + normalization
pipeline introduced in the corpus-classification-and-normalization plan.

Members (Python identifier → wire value):
    NODE_ROOT_CONTRACT   → "node_root_contract"
    HANDLER_CONTRACT     → "handler_contract"
    PACKAGE_CONTRACT     → "package_contract"
    INTEGRATION_CONTRACT → "integration_contract"
    SERVICE_CONTRACT     → "service_contract"
    FIXTURE_OR_TEST      → "fixture_or_test"
    UNKNOWN              → "unknown"
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumContractBucket(str, Enum):
    """Corpus classification bucket for a contract YAML file.

    Inherits from ``str`` so values JSON-serialize without extra logic.
    Pre-validation classifier output; consumed by the per-family
    normalization pipeline before strict Pydantic validation runs.
    """

    NODE_ROOT_CONTRACT = "node_root_contract"
    HANDLER_CONTRACT = "handler_contract"
    PACKAGE_CONTRACT = "package_contract"
    INTEGRATION_CONTRACT = "integration_contract"
    SERVICE_CONTRACT = "service_contract"
    FIXTURE_OR_TEST = "fixture_or_test"
    UNKNOWN = "unknown"


__all__ = ["EnumContractBucket"]

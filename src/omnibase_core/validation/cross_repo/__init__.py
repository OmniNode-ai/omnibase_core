"""Cross-repo conformance validation.

This module provides validators for enforcing code placement,
import boundaries, topic conventions, and error taxonomy
across ONEX repositories.

The validators live in core; repo-specific policy lives in each
repo's onex_validation_policy.yaml.

Related ticket: OMN-1771
"""

from __future__ import annotations

from omnibase_core.validation.cross_repo.engine import (
    CrossRepoValidationEngine,
    run_cross_repo_validation,
)
from omnibase_core.validation.cross_repo.policy_loader import load_policy
from omnibase_core.validation.cross_repo.rule_registry import (
    RuleRegistry,
    get_rule_config_type,
)
from omnibase_core.validation.cross_repo.rules import (
    RuleForbiddenImports,
    RuleRepoBoundaries,
)
from omnibase_core.validation.cross_repo.scanners import (
    ModelFileImports,
    ModelImportInfo,
    ScannerFileDiscovery,
    ScannerImportGraph,
)

__all__ = [
    "CrossRepoValidationEngine",
    "ModelFileImports",
    "ModelImportInfo",
    "RuleForbiddenImports",
    "RuleRegistry",
    "RuleRepoBoundaries",
    "ScannerFileDiscovery",
    "ScannerImportGraph",
    "get_rule_config_type",
    "load_policy",
    "run_cross_repo_validation",
]

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Security domain models for ONEX.

Deprecated Aliases (OMN-1071)
-----------------------------
Deprecated aliases for classes renamed in v0.4.0.
The following aliases will be removed in a future version:

- ``ModelSecurityUtils`` -> use ``UtilSecurity`` from ``omnibase_core.utils.util_security``

The ``__getattr__`` function provides lazy loading with deprecation warnings
to help users migrate to the new names.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_approval_requirements import ModelApprovalRequirements
    from .model_audit_requirements import ModelAuditRequirements
    from .model_network_restrictions import ModelNetworkRestrictions
    from .model_password_policy import ModelPasswordPolicy
    from .model_permission import ModelPermission
    from .model_permission_action import ModelPermissionAction
    from .model_permission_condition import ModelPermissionCondition
    from .model_permission_constraint_metadata import ModelPermissionConstraintMetadata
    from .model_permission_constraints import ModelPermissionConstraints
    from .model_permission_custom_constraints import ModelPermissionCustomConstraints
    from .model_permission_scope import ModelPermissionScope
    from .model_permission_session_info import ModelPermissionSessionInfo
    from .model_policy_value import ModelPolicyValue
    from .model_risk_assessment import ModelRiskAssessment
    from .model_secret_backend import ModelSecretBackend
    from .model_secret_config import ModelSecretConfig
    from .model_secret_management import (
        create_secret_manager_for_environment,
        get_secret_manager,
        get_security_recommendations,
        init_secret_manager,
        init_secret_manager_from_manager,
        validate_secret_configuration,
    )
    from .model_secret_manager import ModelSecretManager
    from .model_secure_credentials import ModelSecureCredentials
    from .model_security_context import ModelSecurityContext
    from .model_security_level import ModelSecurityLevel
    from .model_security_policy import ModelSecurityPolicy
    from .model_security_rule import ModelSecurityRule
    from .model_session_policy import ModelSessionPolicy

__all__ = [
    "ModelApprovalRequirements",
    "ModelAuditRequirements",
    "ModelNetworkRestrictions",
    "ModelPasswordPolicy",
    "ModelPermission",
    "ModelPermissionAction",
    "ModelPermissionCondition",
    "ModelPermissionConstraintMetadata",
    "ModelPermissionConstraints",
    "ModelPermissionCustomConstraints",
    "ModelPermissionScope",
    "ModelPermissionSessionInfo",
    "ModelPolicyValue",
    "ModelRiskAssessment",
    "ModelSecretBackend",
    "ModelSecretConfig",
    "ModelSecretManager",
    "ModelSecureCredentials",
    "ModelSecurityContext",
    "ModelSecurityLevel",
    "ModelSecurityPolicy",
    "ModelSecurityRule",
    "ModelSessionPolicy",
    "create_secret_manager_for_environment",
    "get_secret_manager",
    "get_security_recommendations",
    "init_secret_manager",
    "init_secret_manager_from_manager",
    "validate_secret_configuration",
    # DEPRECATED: Use UtilSecurity from omnibase_core.utils instead
    "ModelSecurityUtils",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelApprovalRequirements": (
        "omnibase_core.models.security.model_approval_requirements",
        "ModelApprovalRequirements",
    ),
    "ModelAuditRequirements": (
        "omnibase_core.models.security.model_audit_requirements",
        "ModelAuditRequirements",
    ),
    "ModelNetworkRestrictions": (
        "omnibase_core.models.security.model_network_restrictions",
        "ModelNetworkRestrictions",
    ),
    "ModelPasswordPolicy": (
        "omnibase_core.models.security.model_password_policy",
        "ModelPasswordPolicy",
    ),
    "ModelPermission": (
        "omnibase_core.models.security.model_permission",
        "ModelPermission",
    ),
    "ModelPermissionAction": (
        "omnibase_core.models.security.model_permission_action",
        "ModelPermissionAction",
    ),
    "ModelPermissionCondition": (
        "omnibase_core.models.security.model_permission_condition",
        "ModelPermissionCondition",
    ),
    "ModelPermissionConstraintMetadata": (
        "omnibase_core.models.security.model_permission_constraint_metadata",
        "ModelPermissionConstraintMetadata",
    ),
    "ModelPermissionConstraints": (
        "omnibase_core.models.security.model_permission_constraints",
        "ModelPermissionConstraints",
    ),
    "ModelPermissionCustomConstraints": (
        "omnibase_core.models.security.model_permission_custom_constraints",
        "ModelPermissionCustomConstraints",
    ),
    "ModelPermissionScope": (
        "omnibase_core.models.security.model_permission_scope",
        "ModelPermissionScope",
    ),
    "ModelPermissionSessionInfo": (
        "omnibase_core.models.security.model_permission_session_info",
        "ModelPermissionSessionInfo",
    ),
    "ModelPolicyValue": (
        "omnibase_core.models.security.model_policy_value",
        "ModelPolicyValue",
    ),
    "ModelRiskAssessment": (
        "omnibase_core.models.security.model_risk_assessment",
        "ModelRiskAssessment",
    ),
    "ModelSecretBackend": (
        "omnibase_core.models.security.model_secret_backend",
        "ModelSecretBackend",
    ),
    "ModelSecretConfig": (
        "omnibase_core.models.security.model_secret_config",
        "ModelSecretConfig",
    ),
    "create_secret_manager_for_environment": (
        "omnibase_core.models.security.model_secret_management",
        "create_secret_manager_for_environment",
    ),
    "get_secret_manager": (
        "omnibase_core.models.security.model_secret_management",
        "get_secret_manager",
    ),
    "get_security_recommendations": (
        "omnibase_core.models.security.model_secret_management",
        "get_security_recommendations",
    ),
    "init_secret_manager": (
        "omnibase_core.models.security.model_secret_management",
        "init_secret_manager",
    ),
    "init_secret_manager_from_manager": (
        "omnibase_core.models.security.model_secret_management",
        "init_secret_manager_from_manager",
    ),
    "validate_secret_configuration": (
        "omnibase_core.models.security.model_secret_management",
        "validate_secret_configuration",
    ),
    "ModelSecretManager": (
        "omnibase_core.models.security.model_secret_manager",
        "ModelSecretManager",
    ),
    "ModelSecureCredentials": (
        "omnibase_core.models.security.model_secure_credentials",
        "ModelSecureCredentials",
    ),
    "ModelSecurityContext": (
        "omnibase_core.models.security.model_security_context",
        "ModelSecurityContext",
    ),
    "ModelSecurityLevel": (
        "omnibase_core.models.security.model_security_level",
        "ModelSecurityLevel",
    ),
    "ModelSecurityPolicy": (
        "omnibase_core.models.security.model_security_policy",
        "ModelSecurityPolicy",
    ),
    "ModelSecurityRule": (
        "omnibase_core.models.security.model_security_rule",
        "ModelSecurityRule",
    ),
    "ModelSessionPolicy": (
        "omnibase_core.models.security.model_session_policy",
        "ModelSessionPolicy",
    ),
}


# =============================================================================
# Deprecated aliases: Lazy-load with warnings per OMN-1071 renaming.
# =============================================================================
def __getattr__(name: str) -> object:
    """
    Lazy re-exports from _LAZY_IMPORTS (OMN-17427), then deprecated aliases
    per OMN-1071 renaming.

    Deprecated Aliases:
    -------------------
    All deprecated aliases emit DeprecationWarning when accessed:
    - ModelSecurityUtils -> UtilSecurity
    """
    target = _LAZY_IMPORTS.get(name)
    if target is not None:
        module = importlib.import_module(target[0])
        value = module if target[1] is None else getattr(module, target[1])
        globals()[name] = value
        return value

    import warnings

    if name == "ModelSecurityUtils":
        warnings.warn(
            "'ModelSecurityUtils' is deprecated, use 'UtilSecurity' "
            "from 'omnibase_core.utils.util_security' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        from omnibase_core.utils.util_security import UtilSecurity

        return UtilSecurity

    # A submodule that the old eager __init__ loaded as a side effect
    # stays reachable as ``package.submodule``: import it on first access.
    if (
        name.isidentifier()
        and not name.startswith("__")
        and importlib.util.find_spec(f"{__name__}.{name}") is not None
    ):
        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(  # error-ok: required for __getattr__ protocol
        f"module {__name__!r} has no attribute {name!r}"
    )


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})

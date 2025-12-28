"""
Security domain models for ONEX.

Deprecated Aliases (OMN-1071)
=============================
This module provides deprecated aliases for classes renamed in v0.4.0.
The following aliases will be removed in a future version:

- ``ModelSecurityUtils`` -> use ``UtilSecurity`` from ``omnibase_core.utils.util_security``

The ``__getattr__`` function provides lazy loading with deprecation warnings
to help users migrate to the new names.
"""

from typing import Any

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


# =============================================================================
# Deprecated aliases: Lazy-load with warnings per OMN-1071 renaming.
# =============================================================================
def __getattr__(name: str) -> Any:
    """
    Lazy loading for deprecated aliases per OMN-1071 renaming.

    Deprecated Aliases:
    -------------------
    All deprecated aliases emit DeprecationWarning when accessed:
    - ModelSecurityUtils -> UtilSecurity
    """
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

    raise AttributeError(  # error-ok: required for __getattr__ protocol
        f"module {__name__!r} has no attribute {name!r}"
    )

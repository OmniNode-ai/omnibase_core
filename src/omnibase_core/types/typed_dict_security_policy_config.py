"""
TypedDict for security policy configuration in tool collections.

Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TypedDictSecurityPolicyConfig(TypedDict, total=False):
    """TypedDict for security policy configuration in tool collections.

    This is a configuration dictionary used in ModelToolCollection for
    security settings. For full security policy models, see ModelSecurityPolicy.

    All fields are optional to support partial configuration.
    """

    # Policy identification
    policy_name: NotRequired[str]
    policy_version: NotRequired[
        str
    ]  # Serialization boundary - string version for config
    description: NotRequired[str]

    # Authentication settings
    require_authentication: NotRequired[bool]
    require_mfa: NotRequired[bool]
    allowed_auth_methods: NotRequired[list[str]]

    # Session settings
    session_timeout_minutes: NotRequired[int]
    max_sessions_per_user: NotRequired[int]

    # Access control
    default_action: NotRequired[str]
    access_control_model: NotRequired[str]

    # Network restrictions
    allowed_ip_ranges: NotRequired[list[str]]
    denied_ip_ranges: NotRequired[list[str]]

    # Compliance
    compliance_frameworks: NotRequired[list[str]]
    data_classification: NotRequired[str]


__all__ = ["TypedDictSecurityPolicyConfig"]

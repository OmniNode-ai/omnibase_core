"""
TypedDict for access control configuration in tool collections.

Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TypedDictAccessControlConfig(TypedDict, total=False):
    """TypedDict for access control configuration in tool collections.

    Defines access control settings for tool collection management.
    All fields are optional to support partial configuration.
    """

    # Role-based access control
    allowed_roles: NotRequired[list[str]]
    denied_roles: NotRequired[list[str]]

    # User-based access control
    allowed_users: NotRequired[list[str]]
    denied_users: NotRequired[list[str]]

    # Permission-based access control
    required_permissions: NotRequired[list[str]]

    # Group-based access control
    allowed_groups: NotRequired[list[str]]
    denied_groups: NotRequired[list[str]]

    # API access control
    allowed_api_keys: NotRequired[list[str]]
    rate_limit_per_minute: NotRequired[int]

    # Resource-level permissions
    read_access: NotRequired[bool]
    write_access: NotRequired[bool]
    execute_access: NotRequired[bool]
    admin_access: NotRequired[bool]


__all__ = ["TypedDictAccessControlConfig"]

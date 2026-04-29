# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumTicketServiceAction(StrEnum):
    """Actions the overseer can request from a ticket service provider.

    Used in protocol dispatch to issue-tracking integrations (e.g. Linear, Jira).
    """

    CREATE_ISSUE = "CREATE_ISSUE"
    """Create a new issue or ticket."""

    UPDATE_ISSUE = "UPDATE_ISSUE"
    """Update fields on an existing issue."""

    GET_ISSUE = "GET_ISSUE"
    """Retrieve a single issue by identifier."""

    LIST_ISSUES = "LIST_ISSUES"
    """List issues matching a query or filter."""

    TRANSITION_STATUS = "TRANSITION_STATUS"
    """Move an issue to a new workflow status."""

    ASSIGN_ISSUE = "ASSIGN_ISSUE"
    """Assign an issue to a user."""

    ADD_COMMENT = "ADD_COMMENT"
    """Append a comment to an issue."""

    DELETE_ISSUE = "DELETE_ISSUE"
    """Delete or archive an issue."""

    LINK_ISSUES = "LINK_ISSUES"
    """Create a relation between two issues."""


__all__: list[str] = ["EnumTicketServiceAction"]

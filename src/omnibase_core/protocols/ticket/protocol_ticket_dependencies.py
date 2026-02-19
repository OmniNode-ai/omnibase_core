# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Protocol definitions for ticket-work automation dependencies.

This module provides protocol interfaces for ticket-work automation components
including Linear API client operations, file system operations for ticket
contracts, and notification delivery.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.ticket import TicketContract


@runtime_checkable
class ProtocolLinearClient(Protocol):
    """
    Protocol for Linear API client operations.

    Implementations provide access to Linear issue data for ticket-work
    automation. The protocol abstracts the Linear GraphQL API to enable
    testing with mock implementations.

    Example implementation:
        class LinearClient:
            def __init__(self, api_key: str) -> None:
                self._api_key = api_key

            def get_issue(self, issue_id: str) -> dict[str, object]:
                # Call Linear GraphQL API
                return {"id": issue_id, "title": "...", ...}
    """

    def get_issue(self, issue_id: str) -> dict[str, object]:
        """
        Fetch issue details from Linear.

        Args:
            issue_id: Linear issue identifier (e.g., "OMN-1807").

        Returns:
            dict[str, object]: Issue data dictionary with the following keys:

            **Required keys** (always present):
              - ``id`` (str): Issue UUID (Linear internal identifier).
              - ``identifier`` (str): Human-readable ID (e.g., ``"OMN-1807"``).
              - ``title`` (str): Issue title.
              - ``description`` (str | None): Issue description in Markdown, or
                ``None`` if no description is set.
              - ``status`` (str): Current workflow state name
                (e.g., ``"Backlog"``, ``"In Progress"``, ``"Done"``).

            **Optional keys** (may be present depending on issue configuration):
              - ``priority`` (dict): Priority info with ``value`` (int 0-4) and
                ``name`` (str).
              - ``labels`` (list[str]): Label names attached to the issue.
              - ``assignee`` (str | None): Assignee display name.
              - ``project`` (str | None): Project name.
              - ``team`` (str): Team name.
              - ``url`` (str): Linear web URL for the issue.
              - ``gitBranchName`` (str): Suggested git branch name.
              - ``createdAt`` (str): ISO-8601 creation timestamp.
              - ``updatedAt`` (str): ISO-8601 last-update timestamp.

        Raises:
            Exception: If the Linear API request fails or the issue is not found.
                Implementations should raise a descriptive exception rather than
                returning an error dict.
        """
        ...


@runtime_checkable
class ProtocolFileSystem(Protocol):
    """
    Protocol for file system operations on ticket contracts.

    Implementations provide file I/O operations for reading, writing, and
    checking existence of ticket contract files. The protocol supports both
    YAML and JSON serialization formats.

    Example implementation:
        class LocalFileSystem:
            def exists(self, path: Path) -> bool:
                return path.exists()

            def read_contract(self, path: Path) -> TicketContract:
                with open(path) as f:
                    data = yaml.safe_load(f)
                return TicketContract.model_validate(data)

            def write_contract(self, path: Path, contract: TicketContract) -> None:
                self.atomic_write(path, contract.to_yaml())

            def atomic_write(self, path: Path, data: str) -> None:
                tmp = path.with_suffix(".tmp")
                tmp.write_text(data)
                tmp.rename(path)
    """

    def exists(self, path: Path) -> bool:
        """
        Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists, False otherwise
        """
        ...

    def read_contract(self, path: Path) -> TicketContract:
        """
        Read and deserialize a ticket contract from file.

        Args:
            path: Path to contract file (YAML or JSON)

        Returns:
            Deserialized TicketContract

        Raises:
            FileNotFoundError: If path does not exist
            ValidationError: If contract is invalid
        """
        ...

    def write_contract(self, path: Path, contract: TicketContract) -> None:
        """
        Serialize and write a ticket contract to file.

        Args:
            path: Destination path
            contract: Contract to write
        """
        ...

    def atomic_write(self, path: Path, data: str) -> None:
        """
        Write data atomically (write to temp, then rename).

        This method ensures that the file is either completely written
        or not modified at all, preventing partial writes on failures.

        Args:
            path: Destination path
            data: String data to write
        """
        ...


@runtime_checkable
class ProtocolNotification(Protocol):
    """
    Protocol for notification delivery (e.g., Slack).

    Implementations deliver notifications when agent automation is blocked
    and requires human intervention. Notifications may be sent to multiple
    channels (Slack, email, etc.) depending on configuration.

    Example implementation:
        class SlackNotifier:
            def __init__(self, webhook_url: str) -> None:
                self._webhook_url = webhook_url

            async def notify_blocked(
                self,
                ticket_id: str,
                reason: str,
                details: list[str],
                repo: str,
            ) -> bool:
                payload = {
                    "text": f"Agent blocked on {ticket_id}",
                    "blocks": [...],
                }
                response = await httpx.post(self._webhook_url, json=payload)
                return response.status_code == 200
    """

    async def notify_blocked(
        self,
        ticket_id: str,
        reason: str,
        details: list[str],
        repo: str,
    ) -> bool:
        """
        Send notification when agent is blocked waiting for human input.

        This method is called when agent automation cannot proceed without
        human intervention, such as when requirements are ambiguous or
        external dependencies are not met.

        Args:
            ticket_id: Linear ticket identifier (e.g., "OMN-1807")
            reason: Why the agent is blocked (brief summary)
            details: List of specific blocking items or questions
            repo: Repository name for context

        Returns:
            True if notification was delivered to at least one channel,
            False if delivery failed or no channels configured.
            Implementations should log failures but not raise exceptions.
        """
        ...


__all__ = [
    "ProtocolFileSystem",
    "ProtocolLinearClient",
    "ProtocolNotification",
]

# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Valkey-backed watch registry for PR status event routing.

Manages two key structures:
- Watchset: ``onex:watchset:{repo}:{pr_number}`` (SET of agent_ids, 2h TTL)
- Reverse index: ``onex:watchbyagent:{agent_id}`` (SET of repo:pr pairs, 2h TTL)

O(1) key lookup via SMEMBERS -- no key pattern scans.

See OMN-2826 Phase 2b for specification.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default TTL for watch registry keys (2 hours)
WATCH_TTL_SECONDS = 7200


@runtime_checkable
class ValkeyClientProtocol(Protocol):
    """Protocol for Valkey (Redis-compatible) client operations.

    This protocol enables pluggable backends -- the actual Valkey client
    is injected via the ONEX ServiceRegistry. For testing, an in-memory
    implementation can be used.
    """

    async def sadd(self, key: str, *members: str) -> int:
        """Add members to a set."""
        ...

    async def srem(self, key: str, *members: str) -> int:
        """Remove members from a set."""
        ...

    async def smembers(self, key: str) -> set[str]:
        """Get all members of a set."""
        ...

    async def expire(self, key: str, seconds: int) -> bool:
        """Set TTL on a key."""
        ...

    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        ...


class FakeValkeyClient:
    """In-memory Valkey client for STANDALONE mode and testing.

    Provides the same interface as a real Valkey client but stores
    data in memory. TTL is not enforced (data persists until explicit
    removal or process exit).
    """

    def __init__(self) -> None:
        self._store: dict[str, set[str]] = {}

    async def sadd(self, key: str, *members: str) -> int:
        """Add members to a set."""
        if key not in self._store:
            self._store[key] = set()
        before = len(self._store[key])
        self._store[key].update(members)
        return len(self._store[key]) - before

    async def srem(self, key: str, *members: str) -> int:
        """Remove members from a set."""
        if key not in self._store:
            return 0
        before = len(self._store[key])
        self._store[key].difference_update(members)
        if not self._store[key]:
            del self._store[key]
        return before - len(self._store.get(key, set()))

    async def smembers(self, key: str) -> set[str]:
        """Get all members of a set."""
        return set(self._store.get(key, set()))

    async def expire(self, key: str, seconds: int) -> bool:
        """Set TTL (no-op for in-memory implementation)."""
        return key in self._store

    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                count += 1
        return count


class WatchRegistry:
    """Valkey-backed watch registry for PR status event routing.

    Manages watchsets and reverse indexes for agent-to-PR subscriptions.
    All operations are idempotent.

    Args:
        client: Valkey client instance (or FakeValkeyClient for testing).
        ttl_seconds: TTL for watch registry keys. Defaults to 7200 (2 hours).
    """

    def __init__(
        self,
        client: ValkeyClientProtocol,
        *,
        ttl_seconds: int = WATCH_TTL_SECONDS,
    ) -> None:
        self._client = client
        self._ttl = ttl_seconds

    @staticmethod
    def _watchset_key(repo: str, pr_number: int) -> str:
        """Build Valkey key for a watchset."""
        return f"onex:watchset:{repo}:{pr_number}"

    @staticmethod
    def _reverse_key(agent_id: str) -> str:
        """Build Valkey key for a reverse index."""
        return f"onex:watchbyagent:{agent_id}"

    async def register_watch(self, agent_id: str, repo: str, pr_number: int) -> bool:
        """Register an agent's interest in a (repo, pr_number) pair.

        Idempotent via SADD. Sets TTL on both watchset and reverse index.

        Args:
            agent_id: The agent identifier.
            repo: Full repo slug (e.g. ``OmniNode-ai/omniclaude``).
            pr_number: PR number to watch.

        Returns:
            True if this was a new registration, False if already registered.
        """
        watchset_key = self._watchset_key(repo, pr_number)
        reverse_key = self._reverse_key(agent_id)
        member = f"{repo}:{pr_number}"

        added = await self._client.sadd(watchset_key, agent_id)
        await self._client.sadd(reverse_key, member)

        # Refresh TTL on both keys
        await self._client.expire(watchset_key, self._ttl)
        await self._client.expire(reverse_key, self._ttl)

        is_new = added > 0
        if is_new:
            logger.info(
                "Watch registered: agent=%s repo=%s pr=%d",
                agent_id,
                repo,
                pr_number,
            )
        return is_new

    async def unregister_watch(self, agent_id: str, repo: str, pr_number: int) -> bool:
        """Remove an agent's watch on a (repo, pr_number) pair.

        Idempotent via SREM.

        Args:
            agent_id: The agent identifier.
            repo: Full repo slug.
            pr_number: PR number.

        Returns:
            True if the watch was removed, False if it didn't exist.
        """
        watchset_key = self._watchset_key(repo, pr_number)
        reverse_key = self._reverse_key(agent_id)
        member = f"{repo}:{pr_number}"

        removed = await self._client.srem(watchset_key, agent_id)
        await self._client.srem(reverse_key, member)

        was_present = removed > 0
        if was_present:
            logger.info(
                "Watch unregistered: agent=%s repo=%s pr=%d",
                agent_id,
                repo,
                pr_number,
            )
        return was_present

    async def get_watchers(self, repo: str, pr_number: int) -> set[str]:
        """Get all agent_ids watching a (repo, pr_number) pair.

        O(1) key lookup, O(n) over the set members.

        Args:
            repo: Full repo slug.
            pr_number: PR number.

        Returns:
            Set of agent_ids watching this PR.
        """
        watchset_key = self._watchset_key(repo, pr_number)
        return await self._client.smembers(watchset_key)

    async def get_agent_watches(self, agent_id: str) -> set[str]:
        """Get all (repo, pr_number) pairs watched by an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            Set of ``repo:pr_number`` strings.
        """
        reverse_key = self._reverse_key(agent_id)
        return await self._client.smembers(reverse_key)

    async def unregister_all_for_agent(self, agent_id: str) -> int:
        """Remove all watches for an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            Number of watches removed.
        """
        reverse_key = self._reverse_key(agent_id)
        watches = await self._client.smembers(reverse_key)

        removed = 0
        for member in watches:
            parts = member.rsplit(":", 1)
            if len(parts) == 2:
                repo, pr_str = parts
                try:
                    pr_number = int(pr_str)
                except ValueError:
                    continue
                watchset_key = self._watchset_key(repo, pr_number)
                await self._client.srem(watchset_key, agent_id)
                removed += 1

        await self._client.delete(reverse_key)
        if removed:
            logger.info(
                "All watches removed: agent=%s count=%d",
                agent_id,
                removed,
            )
        return removed

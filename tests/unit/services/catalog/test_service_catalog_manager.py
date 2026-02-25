#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ServiceCatalogManager — OMN-2544.

Covers:
    - fresh fetch: refresh() fetches from registry, writes cache, builds catalog
    - cache hit: load() reads from cache without touching registry
    - signature failure: tampered signature raises CatalogSignatureError on
      both refresh() and load()
    - policy filtering: role, org, deprecated, experimental, allowlist, denylist
    - CLI version mismatch: load() raises CatalogVersionError on mismatch
    - diff: added / removed / updated / deprecated detection
    - offline operation: load-only mode (no registry) works after refresh
    - get_command / list_commands / is_visible / cache_key public API
    - thread safety (basic): concurrent refresh and list_commands do not corrupt
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from omnibase_core.crypto.crypto_ed25519_signer import generate_keypair, sign_base64
from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.models.catalog.model_catalog_policy import ModelCatalogPolicy
from omnibase_core.models.contracts.model_cli_contribution import (
    ModelCliCommandEntry,
    ModelCliContribution,
    ModelCliInvocation,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.services.catalog.service_catalog_manager import (
    CatalogLoadError,
    CatalogSignatureError,
    CatalogVersionError,
    ServiceCatalogManager,
)
from omnibase_core.services.registry.service_registry_cli_contribution import (
    ServiceRegistryCliContribution,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_invocation(
    invocation_type: EnumCliInvocationType = EnumCliInvocationType.KAFKA_EVENT,
) -> ModelCliInvocation:
    """Build a minimal valid invocation spec."""
    return ModelCliInvocation(
        invocation_type=invocation_type,
        topic="onex.cmd.test.v1"
        if invocation_type == EnumCliInvocationType.KAFKA_EVENT
        else None,
        callable_ref=(
            "omnibase_core.test.callable"
            if invocation_type == EnumCliInvocationType.DIRECT_CALL
            else None
        ),
    )


def _make_command(
    cmd_id: str = "com.omninode.test.run",
    group: str = "test",
    permissions: list[str] | None = None,
    visibility: EnumCliCommandVisibility = EnumCliCommandVisibility.PUBLIC,
    risk: EnumCliCommandRisk = EnumCliCommandRisk.LOW,
    requires_hitl: bool = False,
) -> ModelCliCommandEntry:
    """Build a minimal valid command entry."""
    return ModelCliCommandEntry(
        id=cmd_id,
        display_name="Test Run",
        description="Execute a test operation.",
        group=group,
        args_schema_ref=f"{cmd_id}.args.v1",
        output_schema_ref=f"{cmd_id}.output.v1",
        invocation=_make_invocation(),
        permissions=permissions or [],
        visibility=visibility,
        risk=risk,
        requires_hitl=requires_hitl,
    )


def _build_contribution(
    commands: list[ModelCliCommandEntry],
    publisher: str = "com.omninode.test",
    keypair: object = None,
    tamper_signature: bool = False,
) -> ModelCliContribution:
    """Build a fully signed (or deliberately tampered) ModelCliContribution."""
    if keypair is None:
        keypair = generate_keypair()

    fingerprint = ModelCliContribution.compute_fingerprint(commands)
    signature = sign_base64(keypair.private_key_bytes, fingerprint.encode("utf-8"))  # type: ignore[attr-defined]

    if tamper_signature:
        # Flip a character to produce an invalid signature.
        signature = ("X" if signature[0] != "X" else "Y") + signature[1:]

    return ModelCliContribution(
        version=ModelSemVer(major=1, minor=0, patch=0),
        publisher=publisher,
        fingerprint=fingerprint,
        signature=signature,
        signer_public_key=keypair.public_key_base64(),  # type: ignore[attr-defined]
        commands=commands,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_cache(tmp_path: Path) -> Path:
    """Return a temp path for the catalog cache file."""
    return tmp_path / "catalog.json"


@pytest.fixture
def registry() -> ServiceRegistryCliContribution:
    """Return a fresh, empty registry."""
    return ServiceRegistryCliContribution()


@pytest.fixture
def cmd_a() -> ModelCliCommandEntry:
    return _make_command("com.omninode.test.alpha", group="test")


@pytest.fixture
def cmd_b() -> ModelCliCommandEntry:
    return _make_command("com.omninode.test.beta", group="test")


@pytest.fixture
def contrib_ab(
    cmd_a: ModelCliCommandEntry,
    cmd_b: ModelCliCommandEntry,
) -> ModelCliContribution:
    return _build_contribution([cmd_a, cmd_b])


# ---------------------------------------------------------------------------
# Phase 0 validation: ModelCatalogPolicy construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelCatalogPolicy:
    """Tests for ModelCatalogPolicy defaults and immutability."""

    def test_default_is_permissive(self) -> None:
        policy = ModelCatalogPolicy()
        assert policy.allowed_roles == set()
        assert policy.blocked_org_tags == set()
        assert not policy.hide_deprecated
        assert not policy.hide_experimental
        assert policy.command_allowlist == set()
        assert policy.command_denylist == set()
        assert policy.cli_version is None

    def test_policy_is_frozen(self) -> None:
        policy = ModelCatalogPolicy()
        with pytest.raises(Exception):
            policy.hide_deprecated = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Fresh fetch: refresh()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRefresh:
    """Tests for ServiceCatalogManager.refresh()."""

    def test_refresh_builds_catalog(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        registry.publish(contrib_ab, verify_signature=True)
        manager = ServiceCatalogManager(
            registry=registry,
            cache_path=tmp_cache,
            cli_version="0.19.0",
        )
        diff = manager.refresh()

        assert len(manager.list_commands()) == 2
        assert diff.added == sorted(
            ["com.omninode.test.alpha", "com.omninode.test.beta"]
        )
        assert diff.removed == []
        assert diff.updated == []

    def test_refresh_writes_cache_file(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        registry.publish(contrib_ab, verify_signature=True)
        manager = ServiceCatalogManager(registry=registry, cache_path=tmp_cache)
        manager.refresh()

        assert tmp_cache.exists()
        data = json.loads(tmp_cache.read_text())
        assert "commands" in data
        assert "signatures" in data
        assert "com.omninode.test.alpha" in data["commands"]

    def test_refresh_without_registry_raises(self, tmp_cache: Path) -> None:
        manager = ServiceCatalogManager(registry=None, cache_path=tmp_cache)
        with pytest.raises(Exception):
            manager.refresh()

    def test_refresh_tampered_signature_raises(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        cmd = _make_command("com.omninode.test.tampered")
        contrib = _build_contribution([cmd], tamper_signature=True)
        # Publish with verify_signature=False so registry accepts it.
        registry.publish(contrib, verify_signature=False)

        manager = ServiceCatalogManager(registry=registry, cache_path=tmp_cache)
        with pytest.raises(CatalogSignatureError):
            manager.refresh()

    def test_refresh_diff_removed(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        """When a command disappears between refreshes, diff.removed is populated."""
        kp = generate_keypair()
        cmd_x = _make_command("com.omninode.test.x")
        cmd_y = _make_command("com.omninode.test.y")

        # First refresh: x + y
        contrib_xy = _build_contribution([cmd_x, cmd_y], keypair=kp)
        registry.publish(contrib_xy, verify_signature=True)

        manager = ServiceCatalogManager(registry=registry, cache_path=tmp_cache)
        manager.refresh()

        # Second refresh: only x (y removed from registry).
        contrib_x_only = _build_contribution([cmd_x], keypair=kp)
        registry.publish(contrib_x_only, replace=True, verify_signature=True)

        diff2 = manager.refresh()
        assert "com.omninode.test.y" in diff2.removed
        assert "com.omninode.test.x" not in diff2.removed

    def test_refresh_diff_updated(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        """When a command's display_name changes, diff.updated is populated."""
        kp = generate_keypair()
        cmd_v1 = _make_command("com.omninode.test.upd")

        # v1
        contrib_v1 = _build_contribution([cmd_v1], keypair=kp)
        registry.publish(contrib_v1, verify_signature=True)

        manager = ServiceCatalogManager(registry=registry, cache_path=tmp_cache)
        manager.refresh()

        # v2 with a changed display_name (same ID).
        cmd_v2 = ModelCliCommandEntry(
            id="com.omninode.test.upd",
            display_name="Updated Name",
            description="Updated description.",
            group="test",
            args_schema_ref="com.omninode.test.upd.args.v1",
            output_schema_ref="com.omninode.test.upd.output.v1",
            invocation=_make_invocation(),
        )
        contrib_v2 = _build_contribution([cmd_v2], keypair=kp)
        registry.publish(contrib_v2, replace=True, verify_signature=True)

        diff2 = manager.refresh()
        assert "com.omninode.test.upd" in diff2.updated

    def test_refresh_diff_deprecated(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        """When a command transitions to DEPRECATED, diff.deprecated is populated."""
        kp = generate_keypair()
        cmd_active = _make_command(
            "com.omninode.test.dep",
            visibility=EnumCliCommandVisibility.PUBLIC,
        )
        contrib_v1 = _build_contribution([cmd_active], keypair=kp)
        registry.publish(contrib_v1, verify_signature=True)

        manager = ServiceCatalogManager(registry=registry, cache_path=tmp_cache)
        manager.refresh()

        cmd_deprecated = _make_command(
            "com.omninode.test.dep",
            visibility=EnumCliCommandVisibility.DEPRECATED,
        )
        contrib_v2 = _build_contribution([cmd_deprecated], keypair=kp)
        registry.publish(contrib_v2, replace=True, verify_signature=True)

        diff2 = manager.refresh()
        assert "com.omninode.test.dep" in diff2.deprecated


# ---------------------------------------------------------------------------
# Cache hit: load()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoad:
    """Tests for ServiceCatalogManager.load()."""

    def test_load_from_cache_no_network(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        registry.publish(contrib_ab, verify_signature=True)
        manager = ServiceCatalogManager(
            registry=registry,
            cache_path=tmp_cache,
            cli_version="0.19.0",
        )
        manager.refresh()

        # Load-only manager (no registry) must succeed.
        loader = ServiceCatalogManager(
            registry=None,
            cache_path=tmp_cache,
            cli_version="0.19.0",
        )
        loader.load()
        assert len(loader.list_commands()) == 2

    def test_load_missing_cache_raises(self, tmp_cache: Path) -> None:
        manager = ServiceCatalogManager(cache_path=tmp_cache)
        with pytest.raises(CatalogLoadError):
            manager.load()

    def test_load_corrupt_cache_raises(self, tmp_cache: Path) -> None:
        tmp_cache.parent.mkdir(parents=True, exist_ok=True)
        tmp_cache.write_text("not valid json", encoding="utf-8")
        manager = ServiceCatalogManager(cache_path=tmp_cache)
        with pytest.raises(CatalogLoadError):
            manager.load()

    def test_load_verifies_signatures(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        """Tamper with cached signature; load() must raise CatalogSignatureError."""
        registry.publish(contrib_ab, verify_signature=True)
        manager = ServiceCatalogManager(
            registry=registry,
            cache_path=tmp_cache,
            cli_version="0.19.0",
        )
        manager.refresh()

        # Tamper with the cached signature.
        data = json.loads(tmp_cache.read_text())
        for pub in data["signatures"]:
            sig = data["signatures"][pub]["signature"]
            data["signatures"][pub]["signature"] = (
                "X" if sig[0] != "X" else "Y"
            ) + sig[1:]
        tmp_cache.write_text(json.dumps(data), encoding="utf-8")

        loader = ServiceCatalogManager(cache_path=tmp_cache, cli_version="0.19.0")
        with pytest.raises(CatalogSignatureError):
            loader.load()

    def test_load_cli_version_mismatch_raises(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        registry.publish(contrib_ab, verify_signature=True)
        manager = ServiceCatalogManager(
            registry=registry,
            cache_path=tmp_cache,
            cli_version="0.18.0",
        )
        manager.refresh()

        # Try loading with a different version.
        loader = ServiceCatalogManager(
            cache_path=tmp_cache,
            cli_version="0.19.0",
        )
        with pytest.raises(CatalogVersionError):
            loader.load()

    def test_load_no_version_check_when_cli_version_empty(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        registry.publish(contrib_ab, verify_signature=True)
        manager = ServiceCatalogManager(
            registry=registry,
            cache_path=tmp_cache,
            cli_version="0.18.0",
        )
        manager.refresh()

        # Loader with no cli_version should skip version check.
        loader = ServiceCatalogManager(
            registry=None,
            cache_path=tmp_cache,
            cli_version="",
        )
        loader.load()  # Must not raise.
        assert len(loader.list_commands()) == 2


# ---------------------------------------------------------------------------
# Policy filtering
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPolicyFiltering:
    """Tests for policy filter logic in refresh()."""

    def _manager_with(
        self,
        registry: ServiceRegistryCliContribution,
        cache_path: Path,
        policy: ModelCatalogPolicy,
    ) -> ServiceCatalogManager:
        return ServiceCatalogManager(
            registry=registry,
            policy=policy,
            cache_path=cache_path,
        )

    def test_denylist_hides_command(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        cmd = _make_command("com.omninode.test.deny")
        registry.publish(_build_contribution([cmd]), verify_signature=True)

        policy = ModelCatalogPolicy(command_denylist={"com.omninode.test.deny"})
        manager = self._manager_with(registry, tmp_cache, policy)
        manager.refresh()

        assert not manager.is_visible("com.omninode.test.deny")
        assert manager.list_commands() == []

    def test_allowlist_overrides_denylist(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        cmd = _make_command("com.omninode.test.both")
        registry.publish(_build_contribution([cmd]), verify_signature=True)

        policy = ModelCatalogPolicy(
            command_allowlist={"com.omninode.test.both"},
            command_denylist={"com.omninode.test.both"},
        )
        manager = self._manager_with(registry, tmp_cache, policy)
        manager.refresh()

        # Allowlist wins.
        assert manager.is_visible("com.omninode.test.both")

    def test_role_filter_hides_command_without_matching_permission(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        cmd_admin = _make_command(
            "com.omninode.test.admin",
            permissions=["role:admin"],
        )
        cmd_public = _make_command(
            "com.omninode.test.public",
            permissions=[],
        )
        registry.publish(
            _build_contribution([cmd_admin, cmd_public]),
            verify_signature=True,
        )

        policy = ModelCatalogPolicy(allowed_roles={"role:user"})
        manager = self._manager_with(registry, tmp_cache, policy)
        manager.refresh()

        # cmd_admin requires role:admin which is not in allowed_roles.
        assert not manager.is_visible("com.omninode.test.admin")
        # cmd_public has no permissions; role filter requires intersection → hidden.
        assert not manager.is_visible("com.omninode.test.public")

    def test_role_filter_shows_command_with_matching_permission(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        cmd = _make_command("com.omninode.test.user-cmd", permissions=["role:user"])
        registry.publish(_build_contribution([cmd]), verify_signature=True)

        policy = ModelCatalogPolicy(allowed_roles={"role:user"})
        manager = self._manager_with(registry, tmp_cache, policy)
        manager.refresh()

        assert manager.is_visible("com.omninode.test.user-cmd")

    def test_hide_deprecated_hides_deprecated_commands(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        cmd_dep = _make_command(
            "com.omninode.test.dep-cmd",
            visibility=EnumCliCommandVisibility.DEPRECATED,
        )
        cmd_pub = _make_command("com.omninode.test.pub-cmd")
        registry.publish(
            _build_contribution([cmd_dep, cmd_pub]),
            verify_signature=True,
        )

        policy = ModelCatalogPolicy(hide_deprecated=True)
        manager = self._manager_with(registry, tmp_cache, policy)
        manager.refresh()

        assert not manager.is_visible("com.omninode.test.dep-cmd")
        assert manager.is_visible("com.omninode.test.pub-cmd")

    def test_hide_experimental_hides_experimental_commands(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        cmd_exp = _make_command(
            "com.omninode.test.exp-cmd",
            visibility=EnumCliCommandVisibility.EXPERIMENTAL,
        )
        cmd_pub = _make_command("com.omninode.test.stable-cmd")
        registry.publish(
            _build_contribution([cmd_exp, cmd_pub]),
            verify_signature=True,
        )

        policy = ModelCatalogPolicy(hide_experimental=True)
        manager = self._manager_with(registry, tmp_cache, policy)
        manager.refresh()

        assert not manager.is_visible("com.omninode.test.exp-cmd")
        assert manager.is_visible("com.omninode.test.stable-cmd")

    def test_org_policy_blocked_tag_hides_command(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        cmd = _make_command(
            "com.omninode.test.restricted",
            permissions=["org:internal-only"],
        )
        cmd_pub = _make_command("com.omninode.test.open")
        registry.publish(
            _build_contribution([cmd, cmd_pub]),
            verify_signature=True,
        )

        policy = ModelCatalogPolicy(blocked_org_tags={"org:internal-only"})
        manager = self._manager_with(registry, tmp_cache, policy)
        manager.refresh()

        assert not manager.is_visible("com.omninode.test.restricted")
        assert manager.is_visible("com.omninode.test.open")

    def test_permissive_policy_shows_all(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        registry.publish(contrib_ab, verify_signature=True)
        manager = ServiceCatalogManager(registry=registry, cache_path=tmp_cache)
        manager.refresh()

        assert len(manager.list_commands()) == 2


# ---------------------------------------------------------------------------
# Public API: get_command / list_commands / is_visible / cache_key
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPublicApi:
    """Tests for get_command, list_commands, is_visible, cache_key."""

    def _loaded_manager(
        self,
        registry: ServiceRegistryCliContribution,
        contrib: ModelCliContribution,
        tmp_cache: Path,
    ) -> ServiceCatalogManager:
        registry.publish(contrib, verify_signature=True)
        manager = ServiceCatalogManager(registry=registry, cache_path=tmp_cache)
        manager.refresh()
        return manager

    def test_get_command_returns_entry(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        manager = self._loaded_manager(registry, contrib_ab, tmp_cache)
        entry = manager.get_command("com.omninode.test.alpha")
        assert entry is not None
        assert entry.id == "com.omninode.test.alpha"

    def test_get_command_returns_none_for_missing(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        manager = self._loaded_manager(registry, contrib_ab, tmp_cache)
        assert manager.get_command("com.nonexistent.cmd") is None

    def test_list_commands_all(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        manager = self._loaded_manager(registry, contrib_ab, tmp_cache)
        commands = manager.list_commands()
        ids = {c.id for c in commands}
        assert ids == {"com.omninode.test.alpha", "com.omninode.test.beta"}

    def test_list_commands_filtered_by_group(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        cmd_a = _make_command("com.omninode.test.a", group="memory")
        cmd_b = _make_command("com.omninode.test.b", group="cli")
        contrib = _build_contribution([cmd_a, cmd_b])
        registry.publish(contrib, verify_signature=True)

        manager = ServiceCatalogManager(registry=registry, cache_path=tmp_cache)
        manager.refresh()

        memory_cmds = manager.list_commands(group="memory")
        assert len(memory_cmds) == 1
        assert memory_cmds[0].id == "com.omninode.test.a"

    def test_is_visible_true_for_known_command(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        manager = self._loaded_manager(registry, contrib_ab, tmp_cache)
        assert manager.is_visible("com.omninode.test.alpha")

    def test_is_visible_false_for_unknown_command(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        manager = self._loaded_manager(registry, contrib_ab, tmp_cache)
        assert not manager.is_visible("com.unknown.command")

    def test_cache_key_is_stable(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        manager = self._loaded_manager(registry, contrib_ab, tmp_cache)
        k1 = manager.cache_key()
        k2 = manager.cache_key()
        assert k1 == k2
        assert len(k1) == 64  # SHA256 hex

    def test_cache_key_changes_when_commands_change(
        self,
        registry: ServiceRegistryCliContribution,
        tmp_cache: Path,
    ) -> None:
        kp = generate_keypair()
        cmd_x = _make_command("com.omninode.test.x")
        registry.publish(
            _build_contribution([cmd_x], keypair=kp),
            verify_signature=True,
        )
        manager = ServiceCatalogManager(registry=registry, cache_path=tmp_cache)
        manager.refresh()
        key1 = manager.cache_key()

        cmd_y = _make_command("com.omninode.test.y")
        registry.publish(
            _build_contribution([cmd_x, cmd_y], keypair=kp),
            replace=True,
            verify_signature=True,
        )
        manager.refresh()
        key2 = manager.cache_key()

        assert key1 != key2


# ---------------------------------------------------------------------------
# Offline operation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOfflineOperation:
    """Verify catalog works without network after first refresh."""

    def test_load_only_manager_has_no_registry(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        # Build cache via a refresh manager.
        registry.publish(contrib_ab, verify_signature=True)
        ServiceCatalogManager(registry=registry, cache_path=tmp_cache).refresh()

        # Load-only manager (no registry reference).
        offline = ServiceCatalogManager(registry=None, cache_path=tmp_cache)
        offline.load()

        assert offline.is_visible("com.omninode.test.alpha")
        assert offline.is_visible("com.omninode.test.beta")

    def test_get_command_after_load_only(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_cache: Path,
    ) -> None:
        registry.publish(contrib_ab, verify_signature=True)
        ServiceCatalogManager(registry=registry, cache_path=tmp_cache).refresh()

        offline = ServiceCatalogManager(registry=None, cache_path=tmp_cache)
        offline.load()

        entry = offline.get_command("com.omninode.test.beta")
        assert entry is not None
        assert entry.group == "test"


# ---------------------------------------------------------------------------
# Thread safety (basic smoke test)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestThreadSafety:
    """Basic thread safety smoke test for concurrent refresh + list_commands."""

    def test_concurrent_refresh_and_list(
        self,
        registry: ServiceRegistryCliContribution,
        contrib_ab: ModelCliContribution,
        tmp_path: Path,
    ) -> None:
        registry.publish(contrib_ab, verify_signature=True)

        errors: list[Exception] = []

        def do_work(idx: int) -> None:
            try:
                cache = tmp_path / f"catalog_{idx}.json"
                manager = ServiceCatalogManager(
                    registry=registry,
                    cache_path=cache,
                )
                manager.refresh()
                _ = manager.list_commands()
                _ = manager.get_command("com.omninode.test.alpha")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=do_work, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"

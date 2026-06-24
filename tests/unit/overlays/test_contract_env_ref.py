# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the core-resident ``${env.VAR}`` overlay expander.

OMN-13559 — ``omnibase_core.overlays.contract_env_ref.expand_contract_env_refs``
is the sanctioned core-resident overlay-resolution surface (the infra-layer
mirror lives in ``omnibase_infra.runtime.overlay.contract_env_ref``; core cannot
import infra). These tests pin the contract:

* ``${env.VAR}`` resolves from the operator environment.
* ``${env.VAR:default}`` uses the inline default when the var is unset.
* An unset var with no inline default expands to the empty string, so the
  caller can fail closed rather than receive a literal placeholder.
"""

from __future__ import annotations

import pytest

from omnibase_core.overlays.contract_env_ref import expand_contract_env_refs

pytestmark = pytest.mark.unit


class TestExpandContractEnvRefs:
    """Behavioral contract for the core overlay env-ref expander."""

    def test_resolves_bound_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMN_TEST_HOST", "db.example")
        assert expand_contract_env_refs("${env.OMN_TEST_HOST}") == "db.example"

    def test_inline_default_used_when_unbound(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMN_TEST_HOST", raising=False)
        assert expand_contract_env_refs("${env.OMN_TEST_HOST:fallback}") == "fallback"

    def test_bound_var_overrides_inline_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OMN_TEST_HOST", "real")
        assert expand_contract_env_refs("${env.OMN_TEST_HOST:fallback}") == "real"

    def test_unbound_no_default_expands_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fail-closed substrate: caller sees empty string, not a placeholder."""
        monkeypatch.delenv("OMN_TEST_HOST", raising=False)
        assert expand_contract_env_refs("${env.OMN_TEST_HOST}") == ""

    def test_embeds_within_surrounding_text(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OMN_TEST_PORT", "5432")
        assert (
            expand_contract_env_refs("host:${env.OMN_TEST_PORT}/db") == "host:5432/db"
        )

    def test_literal_without_ref_passes_through(self) -> None:
        assert (
            expand_contract_env_refs("bolt://memgraph:7687") == "bolt://memgraph:7687"
        )

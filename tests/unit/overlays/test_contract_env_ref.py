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

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.overlays.contract_env_ref import (
    contract_env_reference,
    expand_contract_env_refs,
    resolve_contract_env_binding,
)

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


class TestResolveContractEnvBinding:
    """Typed, presence-preserving resolution of a single reference (OMN-17554).

    ``expand_contract_env_refs`` cannot distinguish an unset variable from one
    set to the empty string — both expand to ``""``. Every configuration
    override loop in this repo turns on exactly that distinction, so the typed
    resolver reports ``bound`` separately from ``value``.
    """

    def test_bound_variable_reports_bound_and_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OMN_TEST_HOST", "db.example")
        binding = resolve_contract_env_binding("${env.OMN_TEST_HOST}")
        assert binding.name == "OMN_TEST_HOST"
        assert binding.bound is True
        assert binding.value == "db.example"
        assert binding.is_configured() is True

    def test_unset_variable_is_unbound_with_no_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMN_TEST_HOST", raising=False)
        binding = resolve_contract_env_binding("${env.OMN_TEST_HOST}")
        assert binding.bound is False
        assert binding.value is None
        assert binding.is_configured() is False

    def test_empty_variable_is_bound_and_distinguishable_from_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The distinction ``expand_contract_env_refs`` throws away."""
        monkeypatch.setenv("OMN_TEST_HOST", "")
        binding = resolve_contract_env_binding("${env.OMN_TEST_HOST}")
        assert binding.bound is True
        assert binding.value == ""
        assert expand_contract_env_refs("${env.OMN_TEST_HOST}") == ""

    def test_inline_default_used_when_unbound(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMN_TEST_HOST", raising=False)
        binding = resolve_contract_env_binding("${env.OMN_TEST_HOST:fallback}")
        assert binding.bound is False
        assert binding.value == "fallback"

    def test_binding_is_frozen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMN_TEST_HOST", "db.example")
        binding = resolve_contract_env_binding("${env.OMN_TEST_HOST}")
        with pytest.raises(ValueError):
            binding.value = "mutated"  # type: ignore[misc]

    @pytest.mark.parametrize(
        "reference",
        [
            "${env.OMN_TEST_HOST",
            "env.OMN_TEST_HOST",
            "",
            "bolt://memgraph:7687",
            "host:${env.OMN_TEST_HOST}/db",
            "${env.OMN_A}${env.OMN_B}",
            "${env.9BAD}",
        ],
    )
    def test_fails_closed_on_anything_but_one_well_formed_reference(
        self, reference: str
    ) -> None:
        with pytest.raises(ModelOnexError):
            resolve_contract_env_binding(reference)


class TestContractEnvReference:
    """Canonical reference rendering for declared-field binding tables."""

    def test_renders_canonical_reference(self) -> None:
        assert contract_env_reference("ONEX_DB_HOST") == "${env.ONEX_DB_HOST}"

    def test_renders_inline_default(self) -> None:
        assert contract_env_reference("ONEX_DB_HOST", "local") == (
            "${env.ONEX_DB_HOST:local}"
        )

    def test_round_trips_through_the_resolver(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ONEX_ROUNDTRIP", "value")
        binding = resolve_contract_env_binding(contract_env_reference("ONEX_ROUNDTRIP"))
        assert binding.value == "value"

    @pytest.mark.parametrize("name", ["9BAD", "HAS-DASH", "HAS SPACE", "", "A.B"])
    def test_fails_closed_on_an_illegal_name(self, name: str) -> None:
        with pytest.raises(ModelOnexError):
            contract_env_reference(name)

    def test_fails_closed_on_a_default_that_would_close_the_reference(self) -> None:
        with pytest.raises(ModelOnexError):
            contract_env_reference("ONEX_X", "bad}value")

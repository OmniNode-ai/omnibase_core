# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
YAML round-trip and unit tests for OMN-9904 scope schema models.

Covers:
- EnumEnforcement: all four values, severity ordering, downgrade guard
- EnumScopeToken: all five values, is_omninode_context()
- ModelScopePredicate: construction, is_universal(), predicate vocabulary
- ModelActivationScope: construction, is_unrestricted()
- ModelApplicabilityScope: applies_when / disabled_when
- ModelArtifactEnforcement: all three tier fields
- ModelEnforcementScope: full triad round-trip from YAML
- ModelUnavailableBehavior: all modes + diagnostics
- YAML round-trips for each enforcement enum value
- YAML round-trips for each unavailable_behavior mode
- disabled_when conflict semantics (documentation test)
"""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_diagnostics_mode import EnumDiagnosticsMode
from omnibase_core.enums.enum_enforcement import EnumEnforcement
from omnibase_core.enums.enum_scope_token import EnumScopeToken
from omnibase_core.enums.enum_unavailable_mode import EnumUnavailableMode
from omnibase_core.models.scope import (
    ModelActivationScope,
    ModelApplicabilityScope,
    ModelArtifactEnforcement,
    ModelEnforcementScope,
    ModelIntegrationFilter,
    ModelRepoFilter,
    ModelScopePredicate,
    ModelStateFilter,
    ModelTicketFilter,
    ModelUnavailableBehavior,
)

ENFORCEMENT_VALUES: tuple[EnumEnforcement, ...] = tuple(
    EnumEnforcement.__members__.values()
)
SCOPE_TOKEN_VALUES: tuple[EnumScopeToken, ...] = tuple(
    EnumScopeToken.__members__.values()
)
UNAVAILABLE_MODE_VALUES: tuple[EnumUnavailableMode, ...] = tuple(
    EnumUnavailableMode.__members__.values()
)
DIAGNOSTICS_MODE_VALUES: tuple[EnumDiagnosticsMode, ...] = tuple(
    EnumDiagnosticsMode.__members__.values()
)

# ---------------------------------------------------------------------------
# EnumEnforcement
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnumEnforcement:
    def test_all_values_round_trip_yaml(self) -> None:
        """Each enforcement value survives yaml.safe_load -> Pydantic round-trip."""
        for member in ENFORCEMENT_VALUES:
            raw = yaml.safe_dump({"enforcement": member.value})
            loaded = yaml.safe_load(raw)
            assert EnumEnforcement(loaded["enforcement"]) == member

    def test_value_strings(self) -> None:
        assert EnumEnforcement.OBSERVE.value == "observe"
        assert EnumEnforcement.WARN.value == "warn"
        assert EnumEnforcement.BLOCK.value == "block"
        assert EnumEnforcement.FAIL_FAST.value == "fail-fast"

    def test_severity_ordering(self) -> None:
        assert EnumEnforcement.OBSERVE < EnumEnforcement.WARN
        assert EnumEnforcement.WARN < EnumEnforcement.BLOCK
        assert EnumEnforcement.BLOCK < EnumEnforcement.FAIL_FAST

    def test_str_representation(self) -> None:
        assert str(EnumEnforcement.BLOCK) == "block"
        assert str(EnumEnforcement.FAIL_FAST) == "fail-fast"

    def test_can_downgrade_to_legal(self) -> None:
        assert EnumEnforcement.can_downgrade_to(
            EnumEnforcement.BLOCK, EnumEnforcement.WARN
        )
        assert EnumEnforcement.can_downgrade_to(
            EnumEnforcement.WARN, EnumEnforcement.OBSERVE
        )
        assert EnumEnforcement.can_downgrade_to(
            EnumEnforcement.BLOCK, EnumEnforcement.BLOCK
        )

    def test_can_downgrade_to_illegal(self) -> None:
        assert not EnumEnforcement.can_downgrade_to(
            EnumEnforcement.WARN, EnumEnforcement.BLOCK
        )
        assert not EnumEnforcement.can_downgrade_to(
            EnumEnforcement.OBSERVE, EnumEnforcement.FAIL_FAST
        )

    def test_ge_le(self) -> None:
        assert EnumEnforcement.BLOCK >= EnumEnforcement.WARN
        assert EnumEnforcement.WARN <= EnumEnforcement.BLOCK

    def test_comparison_type_error(self) -> None:
        result = EnumEnforcement.BLOCK.__lt__("not_an_enforcement")
        assert result is NotImplemented


# ---------------------------------------------------------------------------
# EnumScopeToken
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnumScopeToken:
    def test_all_values(self) -> None:
        assert EnumScopeToken.OMNINODE_REPO.value == "omninode_repo"
        assert EnumScopeToken.OMNINODE_WORKTREE.value == "omninode_worktree"
        assert EnumScopeToken.OMNINODE_HOME.value == "omninode_home"
        assert EnumScopeToken.EXTERNAL_REPO.value == "external_repo"
        assert EnumScopeToken.UNKNOWN.value == "unknown"

    def test_is_omninode_context(self) -> None:
        assert EnumScopeToken.OMNINODE_REPO.is_omninode_context()
        assert EnumScopeToken.OMNINODE_WORKTREE.is_omninode_context()
        assert EnumScopeToken.OMNINODE_HOME.is_omninode_context()
        assert not EnumScopeToken.EXTERNAL_REPO.is_omninode_context()
        assert not EnumScopeToken.UNKNOWN.is_omninode_context()

    def test_yaml_round_trip(self) -> None:
        for token in SCOPE_TOKEN_VALUES:
            raw = yaml.safe_dump({"token": token.value})
            loaded = yaml.safe_load(raw)
            assert EnumScopeToken(loaded["token"]) == token


# ---------------------------------------------------------------------------
# ModelScopePredicate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelScopePredicate:
    def test_default_is_universal(self) -> None:
        pred = ModelScopePredicate()
        assert pred.is_universal()

    def test_with_cwd_in_not_universal(self) -> None:
        pred = ModelScopePredicate(cwd_in=[EnumScopeToken.OMNINODE_REPO])
        assert not pred.is_universal()

    def test_with_repo_filter(self) -> None:
        pred = ModelScopePredicate(repo=ModelRepoFilter(kind="omninode"))
        assert pred.repo is not None
        assert pred.repo.kind == "omninode"
        assert not pred.is_universal()

    def test_with_ticket_filter(self) -> None:
        pred = ModelScopePredicate(ticket=ModelTicketFilter(namespace="OMN"))
        assert pred.ticket is not None
        assert pred.ticket.namespace == "OMN"

    def test_with_state_filter(self) -> None:
        pred = ModelScopePredicate(
            state=ModelStateFilter(requires=["ONEX_STATE_DIR", "evidence_dir"])
        )
        assert pred.state is not None
        assert "ONEX_STATE_DIR" in pred.state.requires

    def test_with_integrations_filter(self) -> None:
        pred = ModelScopePredicate(
            integrations=ModelIntegrationFilter(
                linear={"workspace": "omninode", "ticket_prefix": "OMN"}
            )
        )
        assert pred.integrations is not None
        assert pred.integrations.linear is not None

    def test_yaml_round_trip_full_predicate(self) -> None:
        data = {
            "cwd_in": ["omninode_repo"],
            "repo": {"kind": "omninode"},
            "ticket": {"namespace": "OMN"},
            "state": {"requires": ["ONEX_STATE_DIR"]},
            "integrations": {"linear": {"workspace": "omninode"}},
        }
        raw = yaml.safe_dump(data)
        loaded = yaml.safe_load(raw)
        pred = ModelScopePredicate.model_validate(loaded)
        assert pred.cwd_in == [EnumScopeToken.OMNINODE_REPO]
        assert pred.repo is not None
        assert pred.ticket is not None
        assert not pred.is_universal()

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelScopePredicate.model_validate({"unknown_field": "value"})

    def test_frozen(self) -> None:
        pred = ModelScopePredicate()
        with pytest.raises(ValidationError, match="frozen_instance"):
            pred.cwd_in = [EnumScopeToken.OMNINODE_REPO]  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ModelActivationScope
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelActivationScope:
    def test_default_is_unrestricted(self) -> None:
        scope = ModelActivationScope()
        assert scope.is_unrestricted()

    def test_with_tokens_not_unrestricted(self) -> None:
        scope = ModelActivationScope(requires_tokens=[EnumScopeToken.OMNINODE_REPO])
        assert not scope.is_unrestricted()

    def test_with_env_not_unrestricted(self) -> None:
        scope = ModelActivationScope(requires_env=["OMNI_HOME"])
        assert not scope.is_unrestricted()

    def test_yaml_round_trip(self) -> None:
        data = {
            "requires_tokens": ["omninode_repo", "omninode_worktree"],
            "requires_env": ["OMNI_HOME", "ONEX_STATE_DIR"],
            "requires_integrations": {"linear": {"workspace": "omninode"}},
        }
        raw = yaml.safe_dump(data)
        loaded = yaml.safe_load(raw)
        scope = ModelActivationScope.model_validate(loaded)
        assert EnumScopeToken.OMNINODE_REPO in scope.requires_tokens
        assert "OMNI_HOME" in scope.requires_env
        assert "linear" in scope.requires_integrations

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelActivationScope.model_validate({"bad_field": True})


# ---------------------------------------------------------------------------
# ModelApplicabilityScope
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelApplicabilityScope:
    def test_defaults(self) -> None:
        scope = ModelApplicabilityScope()
        assert scope.applies_when.is_universal()
        assert scope.disabled_when.is_universal()

    def test_applies_when_set(self) -> None:
        scope = ModelApplicabilityScope(
            applies_when=ModelScopePredicate(repo=ModelRepoFilter(kind="omninode"))
        )
        assert scope.applies_when.repo is not None

    def test_disabled_when_set(self) -> None:
        scope = ModelApplicabilityScope(
            disabled_when=ModelScopePredicate(repo=ModelRepoFilter(kind="external"))
        )
        assert scope.disabled_when.repo is not None

    def test_yaml_round_trip(self) -> None:
        data = {
            "applies_when": {"repo": {"kind": "omninode"}},
            "disabled_when": {"repo": {"kind": "external"}},
        }
        raw = yaml.safe_dump(data)
        loaded = yaml.safe_load(raw)
        scope = ModelApplicabilityScope.model_validate(loaded)
        assert scope.applies_when.repo is not None
        assert scope.disabled_when.repo is not None
        assert scope.applies_when.repo.kind == "omninode"
        assert scope.disabled_when.repo.kind == "external"


# ---------------------------------------------------------------------------
# ModelArtifactEnforcement
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelArtifactEnforcement:
    def test_defaults(self) -> None:
        enf = ModelArtifactEnforcement()
        assert enf.default == EnumEnforcement.BLOCK
        assert enf.non_matching_scope == EnumEnforcement.OBSERVE
        assert enf.missing_dependency == EnumEnforcement.OBSERVE

    def test_all_fields_configurable(self) -> None:
        enf = ModelArtifactEnforcement(
            default=EnumEnforcement.WARN,
            non_matching_scope=EnumEnforcement.WARN,
            missing_dependency=EnumEnforcement.BLOCK,
        )
        assert enf.default == EnumEnforcement.WARN
        assert enf.non_matching_scope == EnumEnforcement.WARN
        assert enf.missing_dependency == EnumEnforcement.BLOCK

    def test_yaml_round_trip_all_enforcement_values(self) -> None:
        """Each enforcement enum value round-trips through YAML for each field."""
        for value in ENFORCEMENT_VALUES:
            data = {
                "default": value.value,
                "non_matching_scope": value.value,
                "missing_dependency": value.value,
            }
            raw = yaml.safe_dump(data)
            loaded = yaml.safe_load(raw)
            enf = ModelArtifactEnforcement.model_validate(loaded)
            assert enf.default == value
            assert enf.non_matching_scope == value
            assert enf.missing_dependency == value


# ---------------------------------------------------------------------------
# ModelUnavailableBehavior
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelUnavailableBehavior:
    def test_defaults(self) -> None:
        ub = ModelUnavailableBehavior()
        assert ub.default == EnumUnavailableMode.HIDDEN
        assert ub.diagnostics == EnumDiagnosticsMode.SILENT

    def test_yaml_round_trip_all_unavailable_modes(self) -> None:
        for mode in UNAVAILABLE_MODE_VALUES:
            data = {"default": mode.value, "diagnostics": "silent"}
            raw = yaml.safe_dump(data)
            loaded = yaml.safe_load(raw)
            ub = ModelUnavailableBehavior.model_validate(loaded)
            assert ub.default == mode

    def test_yaml_round_trip_diagnostics_explain(self) -> None:
        data = {"default": "hidden", "diagnostics": "explain"}
        raw = yaml.safe_dump(data)
        loaded = yaml.safe_load(raw)
        ub = ModelUnavailableBehavior.model_validate(loaded)
        assert ub.diagnostics == EnumDiagnosticsMode.EXPLAIN

    def test_all_enum_values_valid(self) -> None:
        for mode in UNAVAILABLE_MODE_VALUES:
            assert mode.value in ("hidden", "noop", "warn", "block")
        for diag in DIAGNOSTICS_MODE_VALUES:
            assert diag.value in ("explain", "silent")

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelUnavailableBehavior.model_validate({"unexpected": True})


# ---------------------------------------------------------------------------
# ModelEnforcementScope (top-level full triad)
# ---------------------------------------------------------------------------


HOOK_YAML = """
activation:
  requires_tokens: [omninode_repo]
  requires_env: [OMNI_HOME]
applicability:
  applies_when:
    repo:
      kind: omninode
    ticket:
      namespace: OMN
    state:
      requires: [ONEX_STATE_DIR, evidence_dir]
  disabled_when:
    repo:
      kind: external
enforcement:
  default: block
  non_matching_scope: observe
  missing_dependency: observe
unavailable_behavior:
  default: hidden
  diagnostics: explain
"""

SKILL_YAML = """
activation:
  requires_tokens: [omninode_repo]
applicability:
  applies_when:
    integrations:
      linear:
        workspace: omninode
        ticket_prefix: OMN
enforcement:
  default: warn
unavailable_behavior:
  default: hidden
  diagnostics: explain
"""


@pytest.mark.unit
class TestModelEnforcementScope:
    def test_default_construction(self) -> None:
        scope = ModelEnforcementScope()
        assert scope.activation.is_unrestricted()
        assert scope.applicability.applies_when.is_universal()
        assert scope.enforcement.default == EnumEnforcement.BLOCK
        assert scope.unavailable_behavior.default == EnumUnavailableMode.HIDDEN

    def test_hook_yaml_round_trip(self) -> None:
        data = yaml.safe_load(HOOK_YAML)
        scope = ModelEnforcementScope.model_validate(data)

        # Activation
        assert EnumScopeToken.OMNINODE_REPO in scope.activation.requires_tokens
        assert "OMNI_HOME" in scope.activation.requires_env

        # Applicability
        assert scope.applicability.applies_when.repo is not None
        assert scope.applicability.applies_when.repo.kind == "omninode"
        assert scope.applicability.applies_when.ticket is not None
        assert scope.applicability.applies_when.ticket.namespace == "OMN"
        assert scope.applicability.applies_when.state is not None
        assert "ONEX_STATE_DIR" in scope.applicability.applies_when.state.requires
        assert scope.applicability.disabled_when.repo is not None
        assert scope.applicability.disabled_when.repo.kind == "external"

        # Enforcement — HOOK_YAML sets observe for non_matching_scope and missing_dependency
        assert scope.enforcement.default == EnumEnforcement.BLOCK
        assert scope.enforcement.non_matching_scope == EnumEnforcement.OBSERVE
        assert scope.enforcement.missing_dependency == EnumEnforcement.OBSERVE

        # Unavailable behavior
        assert scope.unavailable_behavior.default == EnumUnavailableMode.HIDDEN
        assert scope.unavailable_behavior.diagnostics == EnumDiagnosticsMode.EXPLAIN

    def test_skill_yaml_round_trip(self) -> None:
        data = yaml.safe_load(SKILL_YAML)
        scope = ModelEnforcementScope.model_validate(data)

        assert EnumScopeToken.OMNINODE_REPO in scope.activation.requires_tokens
        assert scope.applicability.applies_when.integrations is not None
        assert scope.applicability.applies_when.integrations.linear is not None
        assert scope.enforcement.default == EnumEnforcement.WARN
        assert scope.unavailable_behavior.diagnostics == EnumDiagnosticsMode.EXPLAIN

    def test_pydantic_serialization_round_trip(self) -> None:
        data = yaml.safe_load(HOOK_YAML)
        scope = ModelEnforcementScope.model_validate(data)
        serialized = scope.model_dump()
        restored = ModelEnforcementScope.model_validate(serialized)
        assert restored == scope

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelEnforcementScope.model_validate({"unknown_top_level": True})

    def test_triad_independence(self) -> None:
        """Activation, applicability, and enforcement are independently configurable."""
        scope = ModelEnforcementScope(
            activation=ModelActivationScope(
                requires_tokens=[EnumScopeToken.OMNINODE_REPO]
            ),
            applicability=ModelApplicabilityScope(
                applies_when=ModelScopePredicate(repo=ModelRepoFilter(kind="omninode"))
            ),
            enforcement=ModelArtifactEnforcement(default=EnumEnforcement.FAIL_FAST),
        )
        assert not scope.activation.is_unrestricted()
        assert not scope.applicability.applies_when.is_universal()
        assert scope.enforcement.default == EnumEnforcement.FAIL_FAST

    def test_disabled_when_wins_documentation(self) -> None:
        """
        Conflict resolution: disabled_when always wins over applies_when.

        This is a documentation test. The scope schema declares the contract;
        the scope evaluator (OMN-9905) enforces it at runtime. The test
        validates that the schema correctly represents both predicates
        simultaneously — a schema that only allowed one or the other would
        prevent declaring the conflict resolution policy.
        """
        scope = ModelEnforcementScope.model_validate(yaml.safe_load(HOOK_YAML))
        # Both predicates are representable in the schema simultaneously.
        # disabled_when.repo.kind == "external" would suppress even if
        # applies_when.repo.kind == "omninode" also matched.
        assert scope.applicability.applies_when.repo is not None
        assert scope.applicability.disabled_when.repo is not None
        # They represent different conditions — schema supports both.
        assert (
            scope.applicability.applies_when.repo.kind
            != scope.applicability.disabled_when.repo.kind
        )

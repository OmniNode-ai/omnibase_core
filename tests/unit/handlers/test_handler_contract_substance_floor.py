# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Adversarial tests for the contract substance floor (OMN-14409).

Ported from onex_change_control (6adc28168d023d027bf9c1172f262ac03c9d9055) for OMN-17427;
the module under test is the omnibase_core port.

The load-bearing property is asymmetric and must be proven in BOTH directions:

* a DoD made entirely of existence probes must FAIL (it certifies nothing), and
* the Evidence-Source autobind stamp path must reject NOTHING.

The second is as important as the first. Downgrading or rejecting autobind
binding receipts would kill the F1 stamp path and push authors back to
hand-authored companions — the exact outcome OMN-14055 exists to prevent.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.ticket.enum_proof_tier import EnumProofTier
from omnibase_core.nodes.node_contract_evidence_check_effect import (
    handler_contract_substance_floor as _mod,
)

derive_proof_tier = _mod.derive_proof_tier
evaluate_contract = _mod.evaluate_contract

# The exact probes the autobind emits (OMN-13317 F1), verbatim from
# contracts/OMN-14400.yaml as minted at commit 97e704f84.
_AUTOBIND_PR_PROBE = (
    "PR_NUMBER=1721 REPO=OmniNode-ai/omnimarket gh pr view ${PR_NUMBER} "
    "--repo ${REPO} --json number,state"
)
_AUTOBIND_SELF_BIND_PROBE = (
    "PR_NUMBER=3971 REPO=OmniNode-ai/onex_change_control gh pr view ${PR_NUMBER} "
    "--repo ${REPO} --json number,state"
)
_SUBSTANTIVE_PROBE = "uv run pytest tests/unit/nodes/node_dod_verify/ -v"


def _write_contract(
    tmp_path: Path, ticket: str, items: list[dict[str, object]]
) -> Path:
    """Serialize a contract via yaml.safe_dump — never string templating.

    Hand-built YAML silently mangles probes containing quotes and colons, which
    is exactly the input class under test here.
    """
    contracts = tmp_path / "contracts"
    contracts.mkdir(exist_ok=True)
    path = contracts / f"{ticket}.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "ticket_id": ticket,
                "title": "test",
                "dod_evidence": items,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _item(
    item_id: str, check_value: str, check_type: str = "command"
) -> dict[str, object]:
    return {
        "id": item_id,
        "checks": [{"check_type": check_type, "check_value": check_value}],
    }


class TestNoOpFamilyIsRejected:
    """A command that cannot fail cannot be evidence.

    The first cut of this gate defaulted UNRECOGNIZED commands to L1, so the
    floor effectively read "any check that is not literally `gh pr view`" — and
    `check_value: "true"` satisfied it. The polarity is now inverted: default
    L0, with an explicit allowlist of falsifiable shapes.
    """

    @pytest.mark.parametrize(
        "probe",
        [
            "true",
            ":",
            "exit 0",
            "echo ok",
            "echo deploy: docker exec omninode-runtime python -c 'import x'",
            "ls",
            "pwd",
            "test -f README.md",
        ],
    )
    def test_no_op_probe_derives_l0(self, probe: str) -> None:
        assert derive_proof_tier("command", probe) is EnumProofTier.L0

    def test_contract_whose_only_check_is_true_fails(self, tmp_path: Path) -> None:
        """The regression that motivated the inversion."""
        path = _write_contract(tmp_path, "OMN-3", [_item("dod-001", "true")])
        assert not evaluate_contract(path).passed

    def test_unrecognized_command_defaults_to_l0(self) -> None:
        """Default REJECT: a probe must be recognizably falsifiable to count."""
        assert derive_proof_tier("command", "frobnicate --widgets") is EnumProofTier.L0

    def test_self_referential_grep_is_identified_but_ungated(self) -> None:
        """The OMN-14417 circular class: correctly identified, deliberately NOT gated.

        Gating it derives L0 and rejects 98.4% of new contract traffic (measured
        2026-07-12), so ``GATE_SELF_REFERENTIAL`` is False until the generator is
        fixed. This pins the *deliberate* current behavior so the flip is a
        conscious act, not an accident.
        """
        probe = "grep -q '^status: PASS$' drift/dod_receipts/OMN-1/dod-001/command.yaml"
        assert _mod.GATE_SELF_REFERENTIAL is False
        assert _mod._SELF_REFERENTIAL_RE.search(probe) is not None
        assert derive_proof_tier("command", probe).satisfies(EnumProofTier.L1)


class TestDeriveProofTier:
    """The tier is derived from the probe — the input OMN-13338 never had."""

    def test_existence_probe_derives_l0(self) -> None:
        assert derive_proof_tier("command", _AUTOBIND_PR_PROBE) is EnumProofTier.L0

    def test_merge_state_probe_derives_l0(self) -> None:
        """`state == MERGED` proves the PR merged, not that the code is right."""
        probe = "gh pr view 1 --repo o/r --json state --jq .state | grep -q MERGED"
        assert derive_proof_tier("command", probe) is EnumProofTier.L0

    def test_diff_assertion_is_substantive(self) -> None:
        """Naming the files the PR must touch IS falsifiable about the change."""
        probe = "gh pr view 1 --repo o/r --json files --jq '[.files[].path]'"
        assert derive_proof_tier("command", probe).satisfies(EnumProofTier.L1)

    def test_ci_outcome_is_substantive(self) -> None:
        """The shape OMN-14425 will have the autobind emit."""
        probe = "gh pr checks 1721 --repo OmniNode-ai/omnimarket"
        assert derive_proof_tier("command", probe).satisfies(EnumProofTier.L1)

    def test_precommit_run_is_substantive(self) -> None:
        assert derive_proof_tier("command", "pre-commit run --all-files").satisfies(
            EnumProofTier.L1
        )


class TestFalsifiableChecksAreAccepted:
    """Rejecting real evidence is the worst failure this gate can have.

    A too-narrow allowlist is a PERVERSE INCENTIVE: if `diff -u expected actual`
    is rejected while a self-referential `grep 'status: PASS'` is accepted (which
    GATE_SELF_REFERENTIAL currently permits), authors are pushed away from real
    evidence and toward the circular pattern this gate exists to eliminate. The
    test is falsifiability — can it FAIL when the work is wrong?
    """

    @pytest.mark.parametrize(
        "probe",
        [
            "./scripts/verify_thing.sh",
            "bash scripts/verify.sh",
            "make verify",
            "jq -e '.status==\"ok\"' out.json",
            "diff -u expected.json actual.json",
            "cmp -s expected.bin actual.bin",
            "uv run validate-yaml contracts/OMN-1.yaml",  # OCC's own validator
            "uv run check-drift",
            "onex validate",
            "python scripts/assert_invariant.py",
            "npm run verify",
        ],
    )
    def test_falsifiable_probe_is_substantive(self, probe: str) -> None:
        assert derive_proof_tier("command", probe).satisfies(EnumProofTier.L1)

    def test_onex_in_a_path_is_not_a_validator_run(self) -> None:
        r"""Regression: an unanchored ``\bonex\b`` matched the PATH, not a command.

        ``gh api .../contents/plugins/onex/skills/...`` is a file-exists probe
        over the API, not a validator run — but nearly every OmniNode path
        contains "onex", so the loose form silently accepted content-free probes.
        The allowlist ratchet caught this on OMN-11220.
        """
        probe = (
            "gh api repos/OmniNode-ai/omniclaude/contents/"
            "plugins/onex/skills/verified_dispatch/SKILL.md"
        )
        assert derive_proof_tier("command", probe) is EnumProofTier.L0

    @pytest.mark.parametrize(
        "probe",
        [
            "gh api repos/o/r/contents/scripts/verify.sh",  # `sh` = file EXTENSION
            "gh api repos/o/r/contents/docs/diff/report.md",  # `diff` = path segment
            "gh api repos/o/r/contents/src/make/build.py",  # `make` = path segment
            "cat scripts/verify.sh",  # prints a file
            "wc -l scripts/deploy.sh",  # counts lines
            "stat src/make/build.py",  # file metadata
        ],
    )
    def test_verb_mentioned_in_a_path_is_not_an_invocation(self, probe: str) -> None:
        r"""A verb counts only when INVOKED — not when mentioned in a path.

        ``\b`` is not enough: ``.`` is a non-word char, so ``\bsh\b`` matches the
        EXTENSION in ``scripts/verify.sh``, and ``\bmake\b``/``\bdiff\b`` match
        path SEGMENTS. ``.sh`` is the most common script extension in this repo,
        so an unanchored ``sh`` accepted every ``gh api .../contents/*.sh``
        file-exists probe as though it were a real script run.

        This is the SAME bug the ratchet caught on ``onex`` — fixed for that one
        token without generalizing to its siblings. When a guard catches one
        token, ask immediately which sibling tokens share the shape.
        """
        assert derive_proof_tier("command", probe) is EnumProofTier.L0

    def test_gh_api_is_rejected_outright(self) -> None:
        """`gh api` is a metadata read — same family as `gh pr view`.

        Rejecting the command is durable; whack-a-mole on its URL path is not,
        because that path routinely contains `.sh` / `make` / `diff` / `onex`.
        """
        probe = "gh api repos/o/r/pulls/1"
        assert derive_proof_tier("command", probe) is EnumProofTier.L0

    @pytest.mark.parametrize(
        "probe",
        [
            "./scripts/verify_thing.sh",
            "bash script.sh",
            "make verify",
            "diff -u expected actual",
            "cd build && make verify",  # after `&&` IS command position
            "uv run validate-yaml contracts/OMN-1.yaml",
            "npm run verify",
        ],
    )
    def test_anchor_does_not_cost_the_legitimate_forms(self, probe: str) -> None:
        assert derive_proof_tier("command", probe).satisfies(EnumProofTier.L1)

    def test_bare_gh_pr_view_derives_l0(self) -> None:
        assert derive_proof_tier("command", "gh pr view 1721") is EnumProofTier.L0

    def test_gh_pr_view_with_status_rollup_is_not_existence(self) -> None:
        """`statusCheckRollup` carries CI signal, so it is not a bare existence
        probe."""
        probe = "gh pr view 1721 --json number,statusCheckRollup"
        assert derive_proof_tier("command", probe).satisfies(EnumProofTier.L1)

    def test_test_probe_derives_l1(self) -> None:
        assert derive_proof_tier("test_passes", _SUBSTANTIVE_PROBE) is EnumProofTier.L1

    def test_runtime_probe_derives_l2(self) -> None:
        probe = "kubectl -n onex-dev get deploy omnidash -o jsonpath='{.spec}'"
        assert derive_proof_tier("command", probe) is EnumProofTier.L2

    def test_empty_probe_derives_l0(self) -> None:
        assert derive_proof_tier("command", "") is EnumProofTier.L0


class TestSubstanceFloor:
    def test_all_existence_dod_fails(self, tmp_path: Path) -> None:
        """The core defect: a DoD made only of existence probes certifies nothing.

        This is contracts/OMN-14400.yaml exactly as the autobind minted it — the
        contract that merged GREEN through every gate (occ-preflight, Receipt
        Gate, Receipt Honesty, Receipt Hardening).
        """
        path = _write_contract(
            tmp_path,
            "OMN-14400",
            [
                _item("dod-OmniNode-ai-omnimarket-pr-1721", _AUTOBIND_PR_PROBE),
                _item("occ-self-bind-pr-3971", _AUTOBIND_SELF_BIND_PROBE),
            ],
        )
        result = evaluate_contract(path)
        assert not result.passed
        assert result.substantive == []
        assert all(f.tier is EnumProofTier.L0 for f in result.findings)

    def test_substantive_item_plus_autobind_binding_items_passes(
        self, tmp_path: Path
    ) -> None:
        """RED -> GREEN: the ONLY delta is one real check. Binding probes stay put."""
        path = _write_contract(
            tmp_path,
            "OMN-14400",
            [
                _item("dod-OmniNode-ai-omnimarket-pr-1721", _AUTOBIND_PR_PROBE),
                _item("occ-self-bind-pr-3971", _AUTOBIND_SELF_BIND_PROBE),
                _item(
                    "dod-behavioral-proof", _SUBSTANTIVE_PROBE, check_type="test_passes"
                ),
            ],
        )
        result = evaluate_contract(path)
        assert result.passed
        assert len(result.substantive) == 1
        # The autobind's two binding probes are still present and still valid —
        # they simply do not COUNT toward the floor.
        assert len(result.findings) == 3

    def test_autobind_stamp_on_contract_with_substantive_item_rejects_nothing(
        self, tmp_path: Path
    ) -> None:
        """The autobind stamp path must have a rejection rate of exactly zero.

        A contract that already carries a real check keeps passing no matter how
        many Evidence-Source binding items the autobind appends to it.
        """
        items = [_item("dod-real", _SUBSTANTIVE_PROBE, check_type="test_passes")]
        for pr in (3971, 3981, 3985, 3986):
            items.append(
                _item(
                    f"occ-self-bind-pr-{pr}",
                    f"gh pr view {pr} --repo OmniNode-ai/onex_change_control "
                    f"--json number,state",
                )
            )
        result = evaluate_contract(_write_contract(tmp_path, "OMN-14409", items))
        assert result.passed, "autobind binding items must never cause a rejection"
        assert len(result.substantive) == 1

    def test_contract_with_no_dod_evidence_is_out_of_scope(
        self, tmp_path: Path
    ) -> None:
        """Whether a contract is REQUIRED is the Receipt Gate's job, not this gate's."""
        path = tmp_path / "contracts" / "OMN-1.yaml"
        path.parent.mkdir(exist_ok=True)
        path.write_text('---\nticket_id: "OMN-1"\ntitle: "t"\n', encoding="utf-8")
        assert evaluate_contract(path).passed

    @pytest.mark.parametrize(
        "probe",
        [
            "grep -q 'def handle' src/omnimarket/nodes/node_x/handler.py",
            "gh pr checks 1721 --repo OmniNode-ai/omnimarket",
            "curl -sf http://localhost:18085/health",
        ],
    )
    def test_falsifiable_probes_are_substantive(
        self, tmp_path: Path, probe: str
    ) -> None:
        """The gate rejects only what is provably content-free, never what is merely
        hard to classify. A static assertion, a CI outcome, and a live readback all
        say something falsifiable about the change."""
        result = evaluate_contract(
            _write_contract(tmp_path, "OMN-2", [_item("dod-001", probe)])
        )
        assert result.passed

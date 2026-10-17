# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for scripts/lint_contract_check_values.py.

Ported from onex_change_control (6adc28168d023d027bf9c1172f262ac03c9d9055) for OMN-17427;
the module under test is the omnibase_core port.

Coverage:
  1. Each anti-pattern category exits non-zero when present
  2. Fail-closed patterns pass (exit 0)
  3. Contracts with no dod_evidence are clean
  4. YAML parse errors are reported
  5. Flat check_value at item level (legacy schema) is also scanned
  6. Multiple findings across multiple files are all reported
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

# ---------------------------------------------------------------------------
from omnibase_core.handlers import handler_contract_check_values_lint as linter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write_contract(tmp_path: Path, check_value: str, dod_id: str = "dod-003") -> Path:
    """Write a minimal contract YAML with one dod_evidence item.

    Uses yaml.dump to ensure complex check_value strings (containing brackets,
    quotes, semicolons) are always serialized as valid YAML.
    """
    data = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-TEST",
        "summary": "test contract",
        "is_seam_ticket": False,
        "interface_change": False,
        "interfaces_touched": [],
        "evidence_requirements": [],
        "dod_evidence": [
            {
                "id": dod_id,
                "description": "CI check",
                "source": "generated",
                "checks": [
                    {
                        "check_type": "command",
                        "check_value": check_value,
                    }
                ],
            }
        ],
        "emergency_bypass": {
            "enabled": False,
            "justification": "",
            "follow_up_ticket_id": "",
        },
    }
    p = tmp_path / "OMN-TEST.yaml"
    p.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8"
    )
    return p


def write_flat_contract(tmp_path: Path, check_value: str) -> Path:
    """Write a contract with check_value at the item level (legacy schema)."""
    data = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-FLAT",
        "dod_evidence": [
            {
                "id": "dod-003",
                "check_value": check_value,
            }
        ],
    }
    p = tmp_path / "OMN-FLAT.yaml"
    p.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8"
    )
    return p


# ---------------------------------------------------------------------------
# Anti-pattern tests — each should produce a non-zero exit
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_empty_permissive_z_pattern(tmp_path: Path) -> None:
    """[ -z "$result" ] || should be flagged as fail-open."""
    bad = '[ -z "$result" ] || [ "$result" = "SUCCESS" ]'
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected findings for: {bad}"
    assert any("empty-permissive" in label for _, label, _ in findings)


@pytest.mark.unit
def test_trailing_or_true(tmp_path: Path) -> None:
    """|| true at the end should be flagged."""
    bad = "some_command || true"
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected findings for: {bad}"
    assert any("trailing || true" in label for _, label, _ in findings)


@pytest.mark.unit
def test_trailing_or_exit_0(tmp_path: Path) -> None:
    """|| exit 0 should be flagged."""
    bad = "some_command || exit 0"
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected findings for: {bad}"
    assert any("trailing || exit 0" in label for _, label, _ in findings)


@pytest.mark.unit
def test_silenced_2_dev_null_at_end(tmp_path: Path) -> None:
    """2>/dev/null at end of fragment (no explicit exit check) should be flagged."""
    bad = "some_command 2>/dev/null"
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected findings for: {bad}"
    assert any("2>/dev/null" in label for _, label, _ in findings)


@pytest.mark.unit
def test_empty_permissive_brace_variable(tmp_path: Path) -> None:
    """Brace-wrapped vars like ${result} in [ -z ... ] || should also be flagged."""
    bad = '[ -z "${result}" ] || [ "$result" = "SUCCESS" ]'
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected findings for: {bad}"
    assert any("empty-permissive" in label for _, label, _ in findings)


@pytest.mark.unit
def test_2_dev_null_mid_fragment_not_flagged(tmp_path: Path) -> None:
    """2>/dev/null at a line boundary with a valid exit check should NOT be flagged.

    Uses \\Z (absolute fragment end) instead of MULTILINE $ to avoid false positives.
    """
    good = 'gh pr checks 1 --repo OmniNode-ai/x 2>/dev/null\n[ "$result" = "OK" ]'
    path = write_contract(tmp_path, good)
    findings = linter.lint_contract(path)
    assert not findings, (
        f"Unexpected findings for valid multi-line fragment: {findings}"
    )


# ---------------------------------------------------------------------------
# Clean / fail-closed patterns — should produce zero findings
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fail_closed_success_check_is_clean(tmp_path: Path) -> None:
    """Canonical fail-closed pattern should not be flagged."""
    check_name = "Validate Contract YAML (OMN-8808)"
    good = (
        "result=$(gh pr view {pr} --repo {repo} --json statusCheckRollup "
        f'-q \'[.statusCheckRollup[] | select(.name == "{check_name}") '
        "| .conclusion] | first // empty'); "
        '[ "$result" = "SUCCESS" ]'
    )
    path = write_contract(tmp_path, good)
    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected findings: {findings}"


@pytest.mark.unit
def test_clean_pr_state_check(tmp_path: Path) -> None:
    """PR state + baseRefName check should not be flagged."""
    good = (
        "state=$(gh pr view {pr} --repo {repo} --json state,baseRefName "
        "-q '[.state, .baseRefName] | @tsv'); "
        '[ "$(echo "$state" | cut -f1)" = "OPEN" ] && '
        '[ "$(echo "$state" | cut -f2)" = "main" ]'
    )
    path = write_contract(tmp_path, good)
    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected findings: {findings}"


@pytest.mark.unit
def test_file_existence_check_is_clean(tmp_path: Path) -> None:
    """test -f ... is fail-closed and should not be flagged."""
    good = "test -f contracts/OMN-TEST.yaml"
    path = write_contract(tmp_path, good)
    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected findings: {findings}"


# ---------------------------------------------------------------------------
# OMN-14431 — inert VAR=literal prefix mixed with runner-substituted ${VAR}
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_inert_pr_number_prefix_is_flagged(tmp_path: Path) -> None:
    """The 'endorsed' workaround (PR_NUMBER=<n> ... ${PR_NUMBER}) must be
    rejected: _substitute_tokens() pre-replaces ${PR_NUMBER} with the
    RUNNER's own PR before the shell ever sees the assignment, so the
    literal is silently discarded and the check targets the wrong PR.
    """
    bad = (
        "PR_NUMBER=1721 REPO=OmniNode-ai/omnimarket "
        "gh pr checks ${PR_NUMBER} --repo ${REPO}"
    )
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected findings for inert-prefix pattern: {bad}"
    assert any("inert-token-prefix" in label for _, label, _ in findings)


@pytest.mark.unit
def test_inert_repo_prefix_is_flagged(tmp_path: Path) -> None:
    """Same defect via the REPO= token in isolation."""
    bad = "REPO=OmniNode-ai/omnimarket gh pr view ${PR_NUMBER} --repo ${REPO}"
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected findings for inert REPO= prefix: {bad}"
    assert any("inert-token-prefix" in label for _, label, _ in findings)


@pytest.mark.unit
def test_genuine_standalone_cross_pr_reference_is_clean(tmp_path: Path) -> None:
    """A hardcoded PR number with NO ${PR_NUMBER} anywhere in the value and a
    literal --repo is the sanctioned, executable-as-written cross-PR pin —
    it must NOT be rejected as a legacy hardcoded PR number.
    """
    good = "gh pr checks 1721 --repo OmniNode-ai/omnimarket"
    path = write_contract(tmp_path, good)
    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected findings for genuine cross-PR pin: {findings}"


@pytest.mark.unit
def test_own_pr_canonical_form_stays_clean(tmp_path: Path) -> None:
    """The plain runner-substituted own-PR form must keep passing."""
    good = "gh pr checks ${PR_NUMBER} --repo ${REPO}"
    path = write_contract(tmp_path, good)
    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected findings for own-PR form: {findings}"


@pytest.mark.unit
def test_hardcoded_pr_mixed_with_token_no_prefix_is_flagged(tmp_path: Path) -> None:
    """Mixing a hardcoded PR number with ${PR_NUMBER} in the same command is
    ambiguous even without a preceding VAR= assignment — reject it via the
    legacy-gh-pr path.
    """
    bad = "gh pr checks 1721 --repo OmniNode-ai/omnimarket ${PR_NUMBER}"
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected findings for mixed hardcoded+token: {bad}"
    assert any(
        "mixed with ${PR_NUMBER}" in label or "inert-token-prefix" in label
        for _, label, _ in findings
    )


@pytest.mark.unit
def test_hardcoded_cross_pr_reference_with_repo_token_is_flagged(
    tmp_path: Path,
) -> None:
    """A hardcoded PR number combined with ${REPO} is rejected: ${REPO}
    resolves to the RUNNER's own repo, not necessarily the repo the pinned
    PR lives in.
    """
    bad = "gh pr checks 1721 --repo ${REPO}"
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected findings for hardcoded PR + \\${{REPO}}: {bad}"
    assert any("legacy-gh-pr" in label for _, label, _ in findings)


@pytest.mark.unit
def test_hardcoded_pr_without_repo_is_flagged(tmp_path: Path) -> None:
    """A hardcoded PR number with no --repo at all is still rejected."""
    bad = "gh pr checks 1721"
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected findings for hardcoded PR w/o --repo: {bad}"
    assert any("legacy-gh-pr" in label for _, label, _ in findings)


@pytest.mark.unit
def test_superseded_inert_prefix_item_is_not_scanned(tmp_path: Path) -> None:
    """Append-only replacement items can supersede immutable historical items.

    The compliance runner skips superseded ids; the linter must mirror that
    behavior so old immutable entries do not block a contract once a later
    executable-as-written replacement exists.
    """
    data = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-SUPERSEDED",
        "dod_evidence": [
            {
                "id": "old-dod",
                "checks": [
                    {
                        "check_type": "command",
                        "check_value": (
                            "PR_NUMBER=1721 REPO=OmniNode-ai/omnimarket "
                            "gh pr view ${PR_NUMBER} --repo ${REPO}"
                        ),
                    }
                ],
            },
            {
                "id": "new-dod",
                "evidence_artifact": "supersedes_dod_evidence:old-dod",
                "checks": [
                    {
                        "check_type": "command",
                        "check_value": (
                            "gh pr view 1721 --repo OmniNode-ai/omnimarket"
                        ),
                    }
                ],
            },
        ],
    }
    path = tmp_path / "OMN-SUPERSEDED.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")

    findings = linter.lint_contract(path)

    assert not findings


# ---------------------------------------------------------------------------
# Edge-case and structural tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_dod_evidence_is_clean(tmp_path: Path) -> None:
    """Contract with no dod_evidence should be clean."""
    data = {"schema_version": "1.0.0", "ticket_id": "OMN-EMPTY", "dod_evidence": []}
    p = tmp_path / "OMN-EMPTY.yaml"
    p.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8"
    )
    findings = linter.lint_contract(p)
    assert not findings


@pytest.mark.unit
def test_yaml_parse_error_reported(tmp_path: Path) -> None:
    """Malformed YAML should produce a yaml-parse-error finding (not crash)."""
    p = tmp_path / "BAD.yaml"
    p.write_text("key: [\n  unclosed bracket\n", encoding="utf-8")
    findings = linter.lint_contract(p)
    assert findings
    assert any("yaml-parse-error" in label for _, label, _ in findings)


@pytest.mark.unit
def test_flat_check_value_at_item_level_is_scanned(tmp_path: Path) -> None:
    """Legacy flat check_value at item level should also be scanned."""
    bad = '[ -z "$result" ] || [ "$result" = "SUCCESS" ]'
    path = write_flat_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, "Flat check_value at item level should be scanned"


# ---------------------------------------------------------------------------
# main() exit-code tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_main_returns_1_for_bad_contract(tmp_path: Path) -> None:
    """main() should return 1 when a bad contract is passed."""
    bad = '[ -z "$result" ] || [ "$result" = "SUCCESS" ]'
    path = write_contract(tmp_path, bad)
    rc = linter.main(["lint_contract_check_values.py", str(path)])
    assert rc == 1


@pytest.mark.unit
def test_main_returns_0_for_clean_contract(tmp_path: Path) -> None:
    """main() should return 0 when no bad patterns are present."""
    good = '[ "$result" = "SUCCESS" ]'
    path = write_contract(tmp_path, good)
    rc = linter.main(["lint_contract_check_values.py", str(path)])
    assert rc == 0


@pytest.mark.unit
def test_main_returns_2_with_no_args() -> None:
    """main() with no file arguments should return 2 (usage error)."""
    rc = linter.main(["lint_contract_check_values.py"])
    assert rc == 2


@pytest.mark.unit
def test_main_reports_all_files(tmp_path: Path) -> None:
    """main() should report findings across multiple files."""
    bad = '[ -z "$result" ] || [ "$result" = "SUCCESS" ]'
    p1 = tmp_path / "A.yaml"
    p2 = tmp_path / "B.yaml"
    for p in (p1, p2):
        data = {
            "dod_evidence": [
                {
                    "id": "dod-003",
                    "checks": [{"check_type": "command", "check_value": bad}],
                }
            ]
        }
        p.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
    rc = linter.main(["lint_contract_check_values.py", str(p1), str(p2)])
    assert rc == 1


# ---------------------------------------------------------------------------
# OMN-15382 Rule A -- executable-command-shape
#
# contracts/OMN-14968.yaml failed dod_verify 3/7: four dod_evidence
# check_values opened with the human-readable prose "Recorded product
# receipt: ..." handed verbatim to `sh -c` by contract_compliance_check.py's
# `_check_command` -- the literal first word "Recorded" fails
# "command not found" (exit 127) every time it is actually executed.
# ---------------------------------------------------------------------------


def write_contract_with_items(
    tmp_path: Path, dod_evidence: list[dict[str, Any]]
) -> Path:
    """Write a minimal contract with an arbitrary dod_evidence list."""
    data = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-TEST",
        "dod_evidence": dod_evidence,
    }
    p = tmp_path / "OMN-TEST.yaml"
    p.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return p


@pytest.mark.unit
def test_rule_a_catches_prose_receipt_prefix(tmp_path: Path) -> None:
    """The OMN-14968 defect: a human-readable "Recorded product receipt: ..."
    description handed verbatim to `sh -c` fails "command not found" (exit
    127) every time it actually runs -- it is not a command at all.
    """
    bad = (
        "Recorded product receipt: uv run pytest "
        "tests/integration/infra/test_dev_runtime_compose_render.py "
        "-k renders_one_runtime_worker_replica"
    )
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected Rule A findings for: {bad}"
    assert any("executable-command-shape" in label for _, label, _ in findings)


@pytest.mark.unit
def test_rule_a_catches_prose_receipt_prefix_pipe_variant(tmp_path: Path) -> None:
    """Same defect class, pipe variant: "Recorded product receipt:
    docker compose ... | sha256sum" -- the literal word "Recorded" still
    fails immediately as a command; stripping only the prose prefix and
    leaving the bare pipe-to-sha256sum would ALSO be vacuously green (`sh`
    has no `pipefail`, and `sha256sum` exits 0 on any input including
    nothing), which is why Rule A's own message names the defect and the
    repaired contracts/OMN-14968.yaml binds this evidence a different way
    entirely (grep against an already-committed hash, not a live re-render).
    """
    bad = (
        "Recorded product receipt: docker compose --env-file "
        "docker/runtime-policy.env -f docker/docker-compose.infra.yml "
        "[-f docker/docker-compose.<lane>.yml] --profile <lane> config "
        "| sha256sum # pre-tree vs post-tree, per lane"
    )
    path = write_contract(tmp_path, bad)
    findings = linter.lint_contract(path)
    assert findings, f"Expected Rule A findings for: {bad}"
    assert any("executable-command-shape" in label for _, label, _ in findings)


@pytest.mark.unit
@pytest.mark.parametrize(
    "good",
    [
        "gh pr view 1721 --repo OmniNode-ai/omnimarket",
        "pre-commit run --all-files",
        "uv run pytest tests/test_x.py -k y",
        "docker compose -f docker-compose.yml config",
        "grep -q 'symbol' src/file.py",
        '[ "$(gh api foo --jq .bar)" = "1" ]',
        "! gh api foo --jq .bar | grep -q x",
        "if test -f contracts/OMN-1.yaml; then grep -q x contracts/OMN-1.yaml; fi",
        "for f in a b c; do test -f $f || exit 1; done",
        'case "${REPO}" in foo) true ;; *) false ;; esac',
        ": ${PR_NUMBER}; gh pr diff $PR_NUMBER --repo OmniNode-ai/omnimarket",
        "PRODUCT_PR_NUMBER=1721 gh pr view $PRODUCT_PR_NUMBER --repo OmniNode-ai/x",
        'state=$(gh pr view {pr} --repo {repo} --json state -q .state); [ "$state" = "OPEN" ]',
        'f="$(mktemp)" && gh api foo --jq .bar > "$f" && grep -q x "$f"',
    ],
)
def test_rule_a_accepts_real_shell_forms(tmp_path: Path, good: str) -> None:
    """Rule A must not flag genuine executable shell fragments, including
    compound/control-flow openers and assignment-prefixed statements (both
    the OMN-14431 literal-prefix idiom and a genuine VAR=$(...) capture).
    """
    path = write_contract(tmp_path, good)
    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected Rule A findings for: {good}: {findings}"


# ---------------------------------------------------------------------------
# OMN-15382 Rule B -- per-item PR binding
#
# contracts/OMN-14968.yaml's dod-OmniNode-ai-omnibase_infra-pr-2536 used the
# OMN-14431 bare ${PR_NUMBER}/${REPO} runner placeholder, so it never actually
# pinned PR #2536 -- it silently re-checked whatever PR the compliance runner
# happened to be evaluating (class-3 PR-number mis-binding).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rule_b_catches_bare_placeholder_in_pr_numbered_item(tmp_path: Path) -> None:
    item = {
        "id": "dod-OmniNode-ai-omnibase_infra-pr-2536",
        "checks": [
            {
                "check_type": "command",
                "check_value": "gh pr view ${PR_NUMBER} --repo ${REPO} --json state",
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert findings, "Expected Rule B finding for bare ${PR_NUMBER} in a PR-numbered id"
    assert any("pr-binding" in label for _, label, _ in findings)


@pytest.mark.unit
def test_rule_b_accepts_literal_pr_pin(tmp_path: Path) -> None:
    item = {
        "id": "dod-OmniNode-ai-omnibase_infra-pr-2536",
        "checks": [
            {
                "check_type": "command",
                "check_value": (
                    "gh pr view 2536 --repo OmniNode-ai/omnibase_infra "
                    "--json number,state"
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected Rule B findings for literal pin: {findings}"


@pytest.mark.unit
def test_rule_b_accepts_generated_product_ci_placeholder(tmp_path: Path) -> None:
    """Generated product diff-scope items intentionally use runner placeholders."""
    item = {
        "id": "dod-OmniNode-ai-omnimarket-pr-321-ci",
        "checks": [
            {
                "check_type": "command",
                "check_value": ("gh pr view ${PR_NUMBER} --repo ${REPO} --json files"),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected Rule B findings for product CI item: {findings}"


@pytest.mark.unit
def test_rule_b_ignores_ids_without_embedded_pr_number(tmp_path: Path) -> None:
    """An id with no `pr-<digits>` (own-PR self-bind form) is out of scope for
    Rule B -- the canonical own-PR form uses the bare ${PR_NUMBER} runner
    placeholder deliberately, and that is correct, not a mis-binding.
    """
    item = {
        "id": "occ-self-bind-pending",
        "checks": [
            {
                "check_type": "command",
                "check_value": "gh pr view ${PR_NUMBER} --repo ${REPO} --json state",
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected findings for non-PR-numbered id: {findings}"


@pytest.mark.unit
def test_rule_b_ignores_items_with_no_gh_pr_call(tmp_path: Path) -> None:
    """A PR-numbered id whose checks never call gh pr view/checks/diff has
    nothing for Rule B to bind (e.g. a pure content probe) -- not this rule's
    concern.
    """
    item = {
        "id": "dod-omnibase_infra-pr-2536-content",
        "checks": [
            {
                "check_type": "command",
                # The ref is incidental to Rule B but must be a real SHA: a
                # placeholder like `abc123` is not a valid abbreviation (GitHub
                # needs >=7 hex) and OMN-15540 Rule F correctly flags it as a
                # deletable ref, which would make this Rule B test fail for an
                # unrelated reason.
                "check_value": (
                    "gh api repos/OmniNode-ai/omnibase_infra/contents/foo.py"
                    "?ref=e09a8327bc94e49ec674e2fba50b45a37c284ba2"
                    " --jq .content | base64 -d | grep -q bar"
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected Rule B findings for non-gh-pr item: {findings}"


@pytest.mark.unit
def test_rule_a_and_b_skip_superseded_items(tmp_path: Path) -> None:
    """Both new rules must respect the append-only supersedes_dod_evidence
    idiom exactly like the pre-existing anti-pattern scan does -- an
    immutable historical item stays reported for audit but is not
    re-evaluated once a later item supersedes it.
    """
    data = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-SUPERSEDED-15382",
        "dod_evidence": [
            {
                "id": "dod-old-pr-2536",
                "checks": [
                    {
                        "check_type": "command",
                        "check_value": "Recorded product receipt: uv run pytest x",
                    }
                ],
            },
            {
                "id": "dod-old-pr-2536-rebind",
                "evidence_artifact": "supersedes_dod_evidence:dod-old-pr-2536",
                "checks": [
                    {
                        "check_type": "command",
                        "check_value": (
                            "gh pr view 2536 --repo OmniNode-ai/omnibase_infra "
                            "--json number,state"
                        ),
                    }
                ],
            },
        ],
    }
    path = tmp_path / "OMN-SUPERSEDED-15382.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")

    findings = linter.lint_contract(path)
    assert not findings, f"Unexpected findings on superseded item: {findings}"


@pytest.mark.unit
def test_rule_a_and_b_repaired_omn_14968_contract_is_clean() -> None:
    """The actual repaired contract this ticket exists to fix must lint clean
    end to end (both pre-existing anti-patterns and the two new OMN-15382
    rules) -- proof the repair, not just a synthetic fixture, is correct.
    """
    contract_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "occ_contract_checks_parity"
        / "OMN-14968.yaml.txt"
    )
    findings = linter.lint_contract(contract_path)
    assert not findings, f"Unexpected findings on repaired OMN-14968.yaml: {findings}"


# ---------------------------------------------------------------------------
# OMN-15391 Rule C: tautological self-comparison
#
# OCC#5481 shipped eight items whose only check was
# `gh pr view <N> ... --jq '.number == <N>' | grep -qx true` -- an `N == N`
# assertion true by construction for every PR that exists. All eight were
# executed at review time and all eight returned rc=0; none can go RED for any
# product reason.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rule_c_catches_shipped_pr_number_tautology(tmp_path: Path) -> None:
    item = {
        "id": "occ-self-bind-5408-lit-rb15391",
        "checks": [
            {
                "check_type": "command",
                "check_value": (
                    "gh pr view 5408 --repo OmniNode-ai/onex_change_control "
                    "--json number --jq '.number == 5408' | grep -qx true"
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert any("tautological-self-comparison" in label for _, label, _ in findings), (
        f"Expected Rule C finding for an `N == N` self-comparison: {findings}"
    )


@pytest.mark.unit
def test_rule_c_catches_gh_api_pulls_endpoint_tautology(tmp_path: Path) -> None:
    """The same tautology written against the REST endpoint instead of `gh pr`."""
    item = {
        "id": "occ-self-bind-api",
        "checks": [
            {
                "check_type": "command",
                "check_value": (
                    "gh api repos/OmniNode-ai/onex_change_control/pulls/5408 "
                    "--jq '.number == 5408' | grep -qx true"
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert any("tautological-self-comparison" in label for _, label, _ in findings)


@pytest.mark.unit
def test_rule_c_allows_comparison_against_a_different_number(tmp_path: Path) -> None:
    """Comparing a selected PR's field to a DIFFERENT literal is falsifiable.

    Negative control: this is exactly the shape a genuine cross-PR assertion
    takes (e.g. asserting a PR's base/head PR number), and it can go RED.
    """
    item = {
        "id": "dod-cross-pr-check",
        "checks": [
            {
                "check_type": "command",
                "check_value": (
                    "gh api repos/OmniNode-ai/omnimarket/pulls/1944 "
                    "--jq '.number == 1945' | grep -qx true"
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert not any(
        "tautological-self-comparison" in label for _, label, _ in findings
    ), f"Rule C must not flag a comparison against a different literal: {findings}"


@pytest.mark.unit
def test_rule_c_allows_substantive_files_probe(tmp_path: Path) -> None:
    """Negative control: reading a PR's file list is not a self-comparison."""
    item = {
        "id": "dod-14979-market1944-scope",
        "checks": [
            {
                "check_type": "command",
                "check_value": (
                    "gh api repos/OmniNode-ai/omnimarket/pulls/1944/files "
                    "--paginate --jq '.[].filename' | grep -qx 'src/foo.py'"
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert not any("tautological-self-comparison" in label for _, label, _ in findings)


# ---------------------------------------------------------------------------
# OMN-15391 Rule D: fail-open zero-count pipe
#
# `check_value`s run under `sh -c` without pipefail. A producer that fails
# emits nothing, `grep -c` prints 0, and `grep -qx 0` exits 0 -- so the leg
# passes GREEN without ever reading what it claims to have read. Proven at
# authoring time: the shipped shape returns rc=0 against a repository that does
# not exist.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rule_d_catches_shipped_zero_count_absence_leg(tmp_path: Path) -> None:
    item = {
        "id": "dod-14979-infra746-bucket-rb15391",
        "checks": [
            {
                "check_type": "command",
                "check_value": (
                    "gh api -H 'Accept: application/vnd.github.raw' "
                    "'repos/OmniNode-ai/omninode_infra/contents/aws/x.tf"
                    "?ref=564e5dba61f396c1be2bbc26949be8e7aba85fb7' "
                    "| grep -c 'push_validation_bundle_reader' | grep -qx 0"
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert any("fail-open-zero-count" in label for _, label, _ in findings), (
        f"Expected Rule D finding for a zero-count absence pipe: {findings}"
    )


@pytest.mark.unit
def test_rule_d_catches_wc_l_and_anchored_zero_variants(tmp_path: Path) -> None:
    """The same fail-open shape written with `wc -l` and an anchored regex."""
    for value in (
        "gh api repos/o/r/contents/f?ref=abc | wc -l | grep -qx 0",
        "gh api repos/o/r/contents/f?ref=abc | grep -c 'MARK' | grep -q '^0$'",
        "gh api repos/o/r/contents/f?ref=abc | grep -cF 'MARK' | grep -qx '0'",
    ):
        item = {
            "id": "dod-variant",
            "checks": [{"check_type": "command", "check_value": value}],
        }
        path = write_contract_with_items(tmp_path, [item])
        findings = linter.lint_contract(path)
        assert any("fail-open-zero-count" in label for _, label, _ in findings), (
            f"Rule D missed fail-open variant: {value!r} -> {findings}"
        )


@pytest.mark.unit
def test_rule_d_allows_fail_closed_read_anchor_absence_form(tmp_path: Path) -> None:
    """Negative control: the sanctioned fail-closed absence idiom is accepted.

    Reads once into a variable, proves the read landed with a positive anchor
    that must be present, and only then asserts absence.
    """
    item = {
        "id": "dod-14980-infra751-writer-rb2",
        "checks": [
            {
                "check_type": "command",
                "check_value": (
                    "body=$(gh api -H 'Accept: application/vnd.github.raw' "
                    "'repos/OmniNode-ai/omninode_infra/contents/aws/x.tf"
                    "?ref=9e2fee7c') "
                    "&& printf '%s' \"$body\" | grep -qF 'PUSH-VALIDATION BUNDLE' "
                    "&& ! printf '%s' \"$body\" | grep -qF 'bundle_writer'"
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert not findings, f"Fail-closed absence idiom must lint clean: {findings}"


@pytest.mark.unit
def test_rule_d_allows_reachability_plus_path_absence_form(tmp_path: Path) -> None:
    """Negative control: the fail-closed form for a path absent at the parent ref."""
    parent = "5703f123" * 5  # a full 40-hex commit sha
    item = {
        "id": "dod-15362-stamp-rb2",
        "checks": [
            {
                "check_type": "command",
                "check_value": (
                    f"gh api 'repos/OmniNode-ai/omniclaude/commits/{parent}' "
                    f"--jq '.sha' | grep -qx '{parent}' "
                    "&& ! gh api 'repos/OmniNode-ai/omniclaude/contents/"
                    ".github/workflows/verifier-stamp-reusable.yml"
                    f"?ref={parent}' --silent"
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert not findings, f"Reachability+absence idiom must lint clean: {findings}"


@pytest.mark.unit
def test_rule_d_allows_nonzero_count_assertions(tmp_path: Path) -> None:
    """Negative control: asserting a count is NOT zero is not the fail-open shape.

    A failed producer yields 0, which fails this assertion -- fail-closed.
    """
    item = {
        "id": "dod-presence",
        "checks": [
            {
                "check_type": "command",
                "check_value": (
                    "gh api repos/o/r/contents/f?ref=abc | grep -c 'MARK' | grep -qx 3"
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert not any("fail-open-zero-count" in label for _, label, _ in findings)


@pytest.mark.unit
def test_rule_c_allows_identity_conjoined_with_falsifiable_predicate(
    tmp_path: Path,
) -> None:
    """Negative control drawn from live corpus text, not invented.

    contracts/OMN-15383.yaml's `occ-self-bind-pr-5437-merged-supersession` ANDs
    the identity comparison with `.state` and `.headRefName` assertions. A
    first draft of Rule C flagged it, which was a FALSE POSITIVE: the extra
    conjuncts are falsifiable (the PR could be OPEN, the branch could be
    renamed), so the check as a whole can go RED. Rule C must fire only when
    the identity comparison is the entire jq program.
    """
    item = {
        "id": "occ-self-bind-pr-5437-merged-supersession",
        "checks": [
            {
                "check_type": "command",
                "check_value": (
                    "gh pr view 5437 --repo OmniNode-ai/onex_change_control "
                    "--json number,state,headRefName "
                    '--jq \'.number == 5437 and .state == "MERGED" '
                    'and .headRefName == "jonah/omn-15383-occ"\''
                ),
            }
        ],
    }
    path = write_contract_with_items(tmp_path, [item])
    findings = linter.lint_contract(path)
    assert not any(
        "tautological-self-comparison" in label for _, label, _ in findings
    ), f"Rule C false-positived on a falsifiable conjunction: {findings}"


# ---------------------------------------------------------------------------
# OMN-15411 Rule E: SIGPIPE-fragile early-exit consumer (WARNING tier)
#
# Every positive control below was MEASURED to reproduce exit 141 under
# `bash -o pipefail -c` against real corpus inputs (5 runs each, 2026-07-29),
# and every negative control was measured to exit 0 on 5/5 runs. Rule E is a
# claim about which shapes are actually exposed, so its tests pin the measured
# outcome rather than the pattern's shape.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rule_e_flags_base64_decoded_body_into_grep_q(tmp_path: Path) -> None:
    """Measured 141,0,141,0,141 -- the first live instance (contracts/OMN-15170)."""
    bad = (
        "gh api repos/jonahgabriel/steel_onslaught/contents/tests/live/"
        "test_omn15170_live_driver.py?ref=24f3f517 --jq .content "
        "| base64 -d | grep -q 'def test_live_match'"
    )
    path = write_contract(tmp_path, bad)
    warnings = linter.lint_contract_warnings(path)
    assert any("sigpipe-fragile" in label for _, label, _ in warnings), warnings


@pytest.mark.unit
def test_rule_e_flags_gh_pr_diff_into_grep_q(tmp_path: Path) -> None:
    """Measured 141,141,0,141,141 on a real PR diff."""
    bad = "gh pr diff 5523 --repo OmniNode-ai/onex_change_control | grep -q 'sigpipe'"
    path = write_contract(tmp_path, bad)
    warnings = linter.lint_contract_warnings(path)
    assert any("sigpipe-fragile" in label for _, label, _ in warnings), warnings


@pytest.mark.unit
def test_rule_e_flags_git_history_walk_into_grep_q(tmp_path: Path) -> None:
    """Measured 141 on 5/5 runs of `git log --oneline -200 | grep -q 'OMN-'`."""
    bad = "git log --oneline -200 | grep -q 'OMN-15411'"
    path = write_contract(tmp_path, bad)
    warnings = linter.lint_contract_warnings(path)
    assert any("sigpipe-fragile" in label for _, label, _ in warnings), warnings


@pytest.mark.unit
def test_rule_e_flags_paginated_list_into_grep_q(tmp_path: Path) -> None:
    bad = (
        "gh api repos/OmniNode-ai/omnimarket/pulls/1944/files --paginate "
        "--jq '.[].filename' | grep -qx 'src/omnimarket/nodes/node_x/handler.py'"
    )
    path = write_contract(tmp_path, bad)
    warnings = linter.lint_contract_warnings(path)
    assert any("sigpipe-fragile" in label for _, label, _ in warnings), warnings


@pytest.mark.unit
def test_rule_e_does_not_flag_scalar_jq_state_probe(tmp_path: Path) -> None:
    """Measured 0 on 5/5 runs. This is the shape OCC#5523 deliberately KEPT.

    `gh` writes one short token and exits before grep reads, so nothing is ever
    written to a closed pipe. Flagging it would contradict the merged repair and
    make Rule E noise across ~180 corpus instances.
    """
    ok = (
        "gh pr view 220 --repo jonahgabriel/steel_onslaught --json state "
        "--jq .state | grep -qx MERGED"
    )
    path = write_contract(tmp_path, ok)
    warnings = linter.lint_contract_warnings(path)
    assert not warnings, f"Rule E false-positived on a measured-safe shape: {warnings}"


@pytest.mark.unit
def test_rule_e_does_not_flag_generated_self_bind_boolean_probe(tmp_path: Path) -> None:
    """Measured 0 on 5/5 runs; also the machine-authored self-bind idiom."""
    ok = (
        "gh api repos/OmniNode-ai/onex_change_control/pulls/5523 "
        "--jq '.state == \"closed\" and .merged_at != null' | grep -qx true"
    )
    path = write_contract(tmp_path, ok)
    warnings = linter.lint_contract_warnings(path)
    assert not warnings, f"Rule E false-positived on a measured-safe shape: {warnings}"


@pytest.mark.unit
def test_rule_e_does_not_flag_the_sanctioned_buffered_repair(tmp_path: Path) -> None:
    """The OCC#7500 here-string replacement idiom must be clean.

    A rule that still fires on its own sanctioned fix is unusable: the
    producer has already exited into a shell variable, and the assertion
    reads that variable via a here-string, which has no pipe stage at all
    for the linter's pipeline scanner to see.

    OMN-16916: an earlier revision of this test (and of the guidance it
    exercises) used `printf '%s' "$body" | grep -qF 'MARKER'` as "the
    sanctioned repair". That form is itself SIGPIPE-fragile once `$body` is
    large -- it is still a pipe into an early-exit `grep -q` consumer. The
    here-string form below is what OMN-15772 actually landed (commit
    4c48f4b40) to fix its own instance of that exact defect.
    """
    ok = (
        'body="$(gh api repos/OmniNode-ai/omnibase_core/contents/README.md'
        '?ref=abc123 --jq .content | base64 -d)" '
        "&& grep -qF 'MARKER' <<< \"$body\""
    )
    path = write_contract(tmp_path, ok)
    warnings = linter.lint_contract_warnings(path)
    assert not warnings, f"Rule E flagged its own sanctioned repair: {warnings}"


@pytest.mark.unit
def test_rule_e_tier2_find_is_advisory_not_fragile(tmp_path: Path) -> None:
    """`find <one-receipt-dir> | grep -q .` measured 0/5 -- advisory tier only.

    84 corpus instances have this exact shape over a directory holding one or
    two receipt files, where `find` finishes writing before grep reads. It is
    reported so a reader knows the shape is volume-dependent, but it is NOT
    ratcheted (see the corpus baseline test).
    """
    borderline = (
        "find drift/dod_receipts/OMN-10081/dod-001 -type f -name '*.yaml' | grep -q ."
    )
    path = write_contract(tmp_path, borderline)
    warnings = linter.lint_contract_warnings(path)
    labels = [label for _, label, _ in warnings]
    assert any("sigpipe-possible" in label for label in labels), labels
    assert not any("sigpipe-fragile" in label for label in labels), labels


@pytest.mark.unit
def test_rule_e_examines_only_the_stage_adjacent_to_grep(tmp_path: Path) -> None:
    """An unbounded producer upstream of a SMALL final stage is not exposed.

    SIGPIPE kills the process holding the write end of the closed pipe -- the
    stage immediately in front of grep. A `base64 -d` two stages back has
    already been drained by `wc -c`, which writes one short line.
    """
    ok = (
        "gh api repos/OmniNode-ai/omnibase_core/contents/README.md?ref=abc123 "
        "--jq .content | base64 -d | wc -c | grep -q '[0-9]'"
    )
    path = write_contract(tmp_path, ok)
    warnings = linter.lint_contract_warnings(path)
    assert not warnings, f"Rule E looked past the adjacent stage: {warnings}"


@pytest.mark.unit
def test_rule_e_skips_superseded_items(tmp_path: Path) -> None:
    """A repaired item must stop being reported once it is superseded.

    Otherwise every OCC#5496-style append-only repair would leave its own
    historical entry warning forever, and the ratchet could never shrink.
    """
    items = [
        {
            "id": "dod-old-fragile",
            "checks": [
                {
                    "check_type": "command",
                    "check_value": (
                        "gh api repos/O/R/contents/f.py?ref=abc --jq .content "
                        "| base64 -d | grep -q 'MARKER'"
                    ),
                }
            ],
        },
        {
            "id": "dod-new-buffered",
            "evidence_artifact": "supersedes_dod_evidence:dod-old-fragile",
            "checks": [
                {
                    "check_type": "command",
                    "check_value": (
                        'body="$(gh api repos/O/R/contents/f.py?ref=abc '
                        '--jq .content | base64 -d)" '
                        "&& grep -qF 'MARKER' <<< \"$body\""
                    ),
                }
            ],
        },
    ]
    path = write_contract_with_items(tmp_path, items)
    warnings = linter.lint_contract_warnings(path)
    assert not warnings, f"Superseded fragile item still reported: {warnings}"


@pytest.mark.unit
def test_rule_e_is_warning_tier_and_does_not_change_exit_code(tmp_path: Path) -> None:
    """The load-bearing property: Rule E must never fail this linter.

    A SIGPIPE false RED fails CLOSED -- it blocks a Done flip, it never passes
    something that should fail -- so it does not warrant blocking a commit that
    merely touches a legacy contract. Growth is stopped by the corpus ratchet in
    test_lint_contract_check_values_corpus_baseline.py instead.
    """
    # The ref must be a real SHA so this isolates Rule E: a placeholder like
    # `abc` is a deletable ref under OMN-15540 Rule F, which IS hard tier, and
    # would make the "no hard findings" assertion below fail for an unrelated
    # reason.
    bad = (
        "gh api repos/O/R/contents/f.py"
        "?ref=e09a8327bc94e49ec674e2fba50b45a37c284ba2 --jq .content "
        "| base64 -d | grep -q 'MARKER'"
    )
    path = write_contract(tmp_path, bad)

    assert linter.lint_contract_warnings(path), "expected a Rule E warning"
    assert not linter.lint_contract(path), (
        "Rule E leaked into the hard-finding path -- it must be warning tier"
    )
    assert linter.main(["lint_contract_check_values.py", str(path)]) == 0


# ---------------------------------------------------------------------------
# OMN-15540 Rule F: predicate pinned to a MUTABLE external state.
#
# The RED-before anchor is the LITERAL check_value from
# contracts/OMN-15484.yaml's `dod-OmniNode-ai-omnibase-infra-pr-2570` item --
# not a paraphrase of it. That check asserts run 30565261108's
# `occ-preflight / eligibility` concluded `failure`; the job was subsequently
# re-run and reads `success`, so the check is a deterministic BLOCK that no
# repair can clear. Against the pre-Rule-F linter these tests fail (the shape
# was invisible); against the shipped linter they pass.
#
# The GREEN-after anchor is the ANCHORED replacement for the same evidence, so
# the rule is shown to discriminate rather than to blanket-reject anything
# mentioning a workflow run.
# ---------------------------------------------------------------------------

# Byte-for-byte the value carried in contracts/OMN-15484.yaml at Rule F
# landing, with the YAML line-fold rejoined as the loader yields it.
_OMN_15484_CHECK_2 = (
    "gh api repos/OmniNode-ai/omnibase_infra/actions/runs/30565261108/jobs "
    "--jq '.jobs[]|select(.name==\"occ-preflight / eligibility\")|.conclusion' "
    "| grep -qx failure"
)

# Same evidence, anchored: the conclusion was RECORDED in a durable receipt at
# observation time, and the check asserts the receipt rather than re-reading a
# surface that has since moved.
_OMN_15484_CHECK_2_ANCHORED = (
    "grep -qx 'conclusion: failure' "
    "drift/dod_receipts/OMN-15484/dod-occ-preflight-eligibility/"
    "2026-07-30T05-14-00Z.yaml"
)


@pytest.mark.unit
def test_rule_f_red_before_on_literal_omn_15484_check_two(tmp_path: Path) -> None:
    """RED-before: the shipped OMN-15484 check-2 bytes are flagged."""
    path = write_contract(tmp_path, _OMN_15484_CHECK_2)
    findings = linter.lint_contract(path)
    labels = [label for _p, label, _f in findings]
    assert any("mutable-state-pin/run-conclusion" in label for label in labels), (
        "The literal contracts/OMN-15484.yaml check-2 value was NOT flagged by "
        f"Rule F. Findings: {labels}"
    )


@pytest.mark.unit
def test_rule_f_green_after_on_anchored_receipt_shape(tmp_path: Path) -> None:
    """GREEN-after: the anchored replacement for the same evidence is clean."""
    path = write_contract(tmp_path, _OMN_15484_CHECK_2_ANCHORED)
    findings = linter.lint_contract(path)
    labels = [label for _p, label, _f in findings]
    assert not any("mutable-state-pin" in label for label in labels), (
        "The anchored receipt-bound replacement was flagged, so Rule F is "
        f"blanket-rejecting rather than discriminating. Findings: {labels}"
    )


@pytest.mark.unit
def test_rule_f_run_conclusion_changes_exit_code(tmp_path: Path) -> None:
    """Rule F is HARD tier -- it must move the linter's exit code."""
    path = write_contract(tmp_path, _OMN_15484_CHECK_2)
    assert linter.main(["lint", str(path)]) == 1


@pytest.mark.unit
def test_rule_f_flags_success_direction_too(tmp_path: Path) -> None:
    """Pinning `success` on a run id is the same unstable read as `failure`."""
    value = (
        "gh api repos/OmniNode-ai/omnibase_infra/actions/runs/30565261108/jobs "
        '--jq \'.jobs[]|select(.name=="merge-hold-gate / evaluate")'
        "|.conclusion' | grep -qx success"
    )
    findings = linter.lint_contract(write_contract(tmp_path, value))
    assert any(
        "mutable-state-pin/run-conclusion" in label for _p, label, _f in findings
    )


@pytest.mark.unit
def test_rule_f_flags_deleted_feature_branch_ref(tmp_path: Path) -> None:
    """The literal contracts/OMN-10765.yaml ref pin (live: HTTP 404)."""
    value = (
        'gh api "repos/OmniNode-ai/omniintelligence/contents/scripts/ci/'
        "detect_test_paths.py?ref=jonah/omn-10765-port-change-aware-test-"
        'selection-to-omniintelligence" --jq .name'
    )
    findings = linter.lint_contract(write_contract(tmp_path, value))
    assert any(
        "mutable-state-pin/deletable-branch-ref" in label for _p, label, _f in findings
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "ref",
    [
        "dev",
        "main",
        "master",
        "refs/heads/dev",
        "e09a8327" * 5,  # full SHA
        "1729c7c3",  # abbreviated SHA (a real omnibase_infra commit)
        "${PRODUCT_HEAD}",  # runner-substituted
        "v1.4.2",  # release tag
    ],
)
def test_rule_f_stable_refs_are_not_flagged(tmp_path: Path, ref: str) -> None:
    """Negative controls: mainline, SHA, tag and dynamic refs are exempt.

    `?ref=dev` in particular is the merged-is-not-deployed discipline (assert
    the fix is live on the mainline), not a defect -- there are 8 such
    instances in the corpus and flagging them would make Rule F noise.
    """
    value = (
        f"gh api 'repos/OmniNode-ai/omnibase_infra/contents/src/x.py?ref={ref}'"
        " --jq .name"
    )
    findings = linter.lint_contract(write_contract(tmp_path, value))
    labels = [label for _p, label, _f in findings]
    assert not any("mutable-state-pin" in label for label in labels), labels


@pytest.mark.unit
def test_rule_f_flags_unanchored_exact_count(tmp_path: Path) -> None:
    """The literal contracts/OMN-15192.yaml `-eq 2` cumulative assertion."""
    value = (
        "COUNT=\"$(gh api 'search/issues?q=repo%3AOmniNode-ai%2F"
        "onex_change_control+is%3Apr+in%3Atitle+%22OCC+companion+for+"
        "OmniNode-ai%2Fomnibase_infra%232536%22' --jq .total_count)\" "
        '&& [ "$COUNT" -eq 2 ]'
    )
    findings = linter.lint_contract(write_contract(tmp_path, value))
    assert any(
        "mutable-state-pin/unanchored-cumulative" in label for _p, label, _f in findings
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("label", "value"),
    [
        (
            "monotone lower bound",
            "gh api 'search/issues?q=repo%3AOmniNode-ai%2Fonex_change_control"
            "+is%3Apr' --jq '.total_count >= 5' | grep -qx true",
        ),
        (
            "is:open bounded",
            "gh api 'search/issues?q=repo%3AOmniNode-ai%2Fonex_change_control"
            "+is%3Apr+is%3Aopen' --jq '.total_count <= 1' | grep -qx true",
        ),
        (
            "closed date range",
            "gh api 'search/issues?q=repo%3AOmniNode-ai%2Fonex_change_control"
            "+is%3Apr+created%3A2026-07-29T03%3A01%3A23Z..2026-07-30T08%3A00%3A00Z'"
            " --jq '.total_count <= 3' | grep -qx true",
        ),
        (
            "zero assertion is Rule D territory",
            "gh api 'search/issues?q=repo%3AOmniNode-ai%2Fonex_change_control"
            "+is%3Apr+created%3A%3E2026-07-29T03%3A01%3A35Z' --jq .total_count"
            " | grep -qx 0",
        ),
    ],
)
def test_rule_f_bounded_or_monotone_counts_are_not_flagged(
    tmp_path: Path, label: str, value: str
) -> None:
    """Negative controls for the unanchored-cumulative detector."""
    findings = linter.lint_contract(write_contract(tmp_path, value))
    labels = [lbl for _p, lbl, _f in findings]
    assert not any("mutable-state-pin" in lbl for lbl in labels), (label, labels)


@pytest.mark.unit
def test_rule_f_ignores_run_id_without_conclusion_assertion(tmp_path: Path) -> None:
    """A run id that is merely fetched, not asserted on, is not a violation."""
    value = (
        "gh api repos/OmniNode-ai/omnibase_infra/actions/runs/30565261108 "
        "--jq .html_url"
    )
    findings = linter.lint_contract(write_contract(tmp_path, value))
    labels = [label for _p, label, _f in findings]
    assert not any("mutable-state-pin" in label for label in labels), labels


# ---------------------------------------------------------------------------
# Rule F: attempt-anchored run reads are the SANCTIONED repair, not a defect.
#
# A run's latest-attempt job record is overwritten by a re-run, but per-attempt
# records are immutable -- a re-run appends attempt N+1 and never rewrites
# attempt N. Verified live against the corpus' own instance (run 30565261108,
# 2026-07-30): `?filter=all` returns attempt 1 = failure alongside attempt 2 =
# success, so the attempt-1 verdict the OMN-15484 evidence needs survives the
# re-run that erased it from the default view.
#
# These tests exist because the first draft of Rule F DID flag this form, and
# the corpus ratchet caught it on the real repair the owning lane had already
# landed on dev. A gate that blocks the fix rather than the defect is a
# false-RED generator; the exemption is pinned here so it cannot regress.
# ---------------------------------------------------------------------------

# Byte-for-byte the repair the infra-unwedge lane landed on dev.
_OMN_15484_ATTEMPT_ANCHORED = (
    "gh api 'repos/OmniNode-ai/omnibase_infra/actions/runs/30565261108/"
    "jobs?filter=all&per_page=100' --jq '.jobs[]|select(.run_attempt==1 and "
    '.name=="occ-preflight / eligibility")|.conclusion\' | grep -qx failure'
)


@pytest.mark.unit
def test_rule_f_exempts_attempt_anchored_filter_all_read(tmp_path: Path) -> None:
    """The landed OMN-15484 repair (filter=all + run_attempt==1) is clean."""
    findings = linter.lint_contract(
        write_contract(tmp_path, _OMN_15484_ATTEMPT_ANCHORED)
    )
    labels = [label for _p, label, _f in findings]
    assert not any("mutable-state-pin" in label for label in labels), (
        "Rule F flagged the attempt-anchored repair, which reads an IMMUTABLE "
        f"per-attempt record. Findings: {labels}"
    )


@pytest.mark.unit
def test_rule_f_exempts_attempts_path_form(tmp_path: Path) -> None:
    """The `/attempts/<n>/jobs` path form is equally attempt-pinned."""
    value = (
        "gh api repos/OmniNode-ai/omnibase_infra/actions/runs/30565261108/"
        "attempts/1/jobs --jq '.jobs[]|select(.name==\"occ-preflight / "
        "eligibility\")|.conclusion' | grep -qx failure"
    )
    findings = linter.lint_contract(write_contract(tmp_path, value))
    labels = [label for _p, label, _f in findings]
    assert not any("mutable-state-pin" in label for label in labels), labels


@pytest.mark.unit
def test_rule_f_still_flags_run_attempt_without_filter_all(tmp_path: Path) -> None:
    """`run_attempt==1` alone is NOT an anchor -- it goes RED on empty input.

    The default jobs endpoint returns only the LATEST attempt, so once the job
    is re-run the selector matches nothing, the producer emits no output, and
    `grep -qx` fails. Same permanent block, different route -- so both halves
    of the exemption are required.
    """
    value = (
        "gh api repos/OmniNode-ai/omnibase_infra/actions/runs/30565261108/jobs "
        "--jq '.jobs[]|select(.run_attempt==1 and .name==\"occ-preflight / "
        "eligibility\")|.conclusion' | grep -qx failure"
    )
    findings = linter.lint_contract(write_contract(tmp_path, value))
    assert any(
        "mutable-state-pin/run-conclusion" in label for _p, label, _f in findings
    ), "run_attempt without filter=all must stay flagged"


@pytest.mark.unit
def test_rule_a_accepts_a_read_only_aws_probe(tmp_path: Path) -> None:
    """OMN-17446: ``aws`` is a command head, not prose.

    Rule A exists to reject a check authored as an English DESCRIPTION of
    something a human already ran, because ``sh -c`` fails such a value on its
    first word. A read-only ``aws ssm get-command-invocation`` readback is the
    opposite: it is how a live cluster measurement is made re-resolvable
    WITHOUT re-running it, which matters because re-running would need
    ``send-command`` and a verifier must not mutate. Pinned here so the
    allowlist entry is a covered decision rather than an untested widening.
    """
    ok = (
        "aws ssm get-command-invocation "
        "--command-id e3d835fc-9445-41b3-9269-b630deeae88a "
        "--instance-id i-06169517a92b45f86 --query Status --output text "
        "| grep -cx Success"
    )
    path = write_contract(tmp_path, ok)
    assert linter.lint_contract(path) == []


@pytest.mark.unit
def test_rule_a_still_rejects_prose_that_merely_mentions_aws(tmp_path: Path) -> None:
    """The control for the test above: widening the allowlist by one real
    command head must not open the door Rule A was built to close."""
    prose = (
        "Recorded readback: aws ssm get-command-invocation was run by hand on "
        "i-06169517a92b45f86 and returned Success"
    )
    path = write_contract(tmp_path, prose)
    assert linter.lint_contract(path), "Rule A must still reject a prose description"

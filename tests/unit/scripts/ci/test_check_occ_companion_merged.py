# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Verdict tests for the occ-companion-merged STRICT gate (OMN-15214).

The gate makes the 2026-07-26 hygiene-sweep trigger state — an OPEN
onex_change_control companion whose product PR has already MERGED —
unreachable via the merge path: the product PR's required ``CI Summary``
context cannot go green until the cited companion is MERGED (or the cited
SHA is already an ancestor of an OCC durable branch).

These tests pin the fail-closed verdict table:

* companion MERGED            → PASS
* companion OPEN              → PENDING (poll; deadline converts to FAIL)
* companion CLOSED unmerged   → FAIL immediately (the incident state)
* SHA ancestor of dev/main    → PASS
* SHA not an ancestor         → FAIL (OMN-15216 strandable pre-merge pin)
* missing Evidence-Source     → PENDING (autobind mint may be in flight)
* malformed Evidence-Source   → FAIL
* dependency-bot author       → PASS (mirrors occ-preflight OMN-13762)
* non-PR event                → PASS (gate not applicable)
* unresolvable PR number      → FAIL (fail closed)
* API errors                  → PENDING (retryable), never PASS
"""

from __future__ import annotations

import pytest

from scripts.ci.check_occ_companion_merged import (
    EXIT_FAIL,
    EXIT_PASS,
    EXIT_PENDING,
    evaluate_once,
    main,
    parse_evidence_source,
    resolve_pr_number,
)

pytestmark = pytest.mark.unit

PRODUCT_REPO = "OmniNode-ai/omnibase_core"
OCC_REPO = "OmniNode-ai/onex_change_control"


class FakeFetcher:
    """Deterministic stand-in for GhFetcher."""

    def __init__(
        self,
        *,
        prs: dict[tuple[str, str], dict[str, object] | None] | None = None,
        compare: dict[tuple[str, str], str | None] | None = None,
    ) -> None:
        self._prs = prs or {}
        self._compare = compare or {}

    def pr_view(self, repo: str, number: str, fields: str) -> dict[str, object] | None:
        return self._prs.get((repo, str(number)))

    def compare_status(self, repo: str, base: str, head_sha: str) -> str | None:
        return self._compare.get((base, head_sha))


def _product_pr(body: str, author: str = "jonahgabriel") -> dict[str, object]:
    return {"body": body, "author": {"login": author}}


def _evaluate(fetcher: FakeFetcher, **kwargs: object):
    defaults: dict[str, object] = {
        "event_name": "pull_request",
        "repo": PRODUCT_REPO,
        "pr_number": "2500",
        "occ_repo": OCC_REPO,
    }
    defaults.update(kwargs)
    return evaluate_once(fetcher, **defaults)  # type: ignore[arg-type]


class TestEvidenceSourceParsing:
    def test_first_line_wins_and_is_case_insensitive(self) -> None:
        body = "intro\nevidence-source:  OCC#5032 \nEvidence-Source: OCC#9999\n"
        assert parse_evidence_source(body) == "OCC#5032"

    def test_absent_returns_none(self) -> None:
        assert parse_evidence_source("no evidence here") is None
        assert parse_evidence_source("") is None

    def test_indented_line_is_not_matched(self) -> None:
        # occ-preflight anchors at line start; mirror it.
        assert parse_evidence_source("  Evidence-Source: OCC#1") is None


class TestPrNumberResolution:
    def test_pull_request_number_passthrough(self) -> None:
        assert resolve_pr_number("pull_request", "123", "") == "123"

    def test_merge_group_head_ref_parse(self) -> None:
        ref = "refs/heads/gh-readonly-queue/dev/pr-456-0123abc"
        assert resolve_pr_number("merge_group", "", ref) == "456"

    def test_unresolvable_returns_empty(self) -> None:
        assert resolve_pr_number("merge_group", "", "refs/heads/whatever") == ""


class TestCompanionPrVerdicts:
    def _fetcher_with_companion(self, occ_state: dict[str, object]) -> FakeFetcher:
        return FakeFetcher(
            prs={
                (PRODUCT_REPO, "2500"): _product_pr("Evidence-Source: OCC#5032"),
                (OCC_REPO, "5032"): occ_state,
            }
        )

    def test_merged_companion_is_pass(self) -> None:
        fetcher = self._fetcher_with_companion(
            {"state": "MERGED", "mergeCommit": {"oid": "abc123"}}
        )
        verdict = _evaluate(fetcher)
        assert verdict.code == EXIT_PASS
        assert "abc123" in verdict.reason

    def test_open_companion_is_pending_not_fail(self) -> None:
        # OPEN may still auto-merge; the poll loop absorbs the latency and the
        # deadline converts PENDING to FAIL.
        fetcher = self._fetcher_with_companion({"state": "OPEN", "mergeCommit": None})
        verdict = _evaluate(fetcher)
        assert verdict.code == EXIT_PENDING
        assert "OPEN" in verdict.reason

    def test_closed_unmerged_companion_is_immediate_fail(self) -> None:
        # The 2026-07-26 incident state: hygiene sweep closed the companion
        # without merging. Evidence destroyed — terminal, never poll.
        fetcher = self._fetcher_with_companion({"state": "CLOSED", "mergeCommit": None})
        verdict = _evaluate(fetcher)
        assert verdict.code == EXIT_FAIL
        assert "CLOSED" in verdict.reason

    def test_companion_fetch_error_is_pending_never_pass(self) -> None:
        fetcher = FakeFetcher(
            prs={
                (PRODUCT_REPO, "2500"): _product_pr("Evidence-Source: OCC#5032"),
                (OCC_REPO, "5032"): None,
            }
        )
        assert _evaluate(fetcher).code == EXIT_PENDING


class TestShaVerdicts:
    SHA = "a" * 40

    def test_sha_ancestor_of_dev_is_pass(self) -> None:
        fetcher = FakeFetcher(
            prs={(PRODUCT_REPO, "2500"): _product_pr(f"Evidence-Source: {self.SHA}")},
            compare={("dev", self.SHA): "behind"},
        )
        assert _evaluate(fetcher).code == EXIT_PASS

    def test_sha_identical_to_main_is_pass(self) -> None:
        fetcher = FakeFetcher(
            prs={(PRODUCT_REPO, "2500"): _product_pr(f"Evidence-Source: {self.SHA}")},
            compare={("dev", self.SHA): "diverged", ("main", self.SHA): "identical"},
        )
        assert _evaluate(fetcher).code == EXIT_PASS

    def test_floating_sha_is_fail(self) -> None:
        # A feature-branch head SHA on squash-only OCC can never become an
        # ancestor of dev/main — terminal (OMN-15216).
        fetcher = FakeFetcher(
            prs={(PRODUCT_REPO, "2500"): _product_pr(f"Evidence-Source: {self.SHA}")},
            compare={("dev", self.SHA): "diverged", ("main", self.SHA): "ahead"},
        )
        verdict = _evaluate(fetcher)
        assert verdict.code == EXIT_FAIL
        assert "ancestor" in verdict.reason

    def test_compare_api_error_is_pending_never_fail(self) -> None:
        fetcher = FakeFetcher(
            prs={(PRODUCT_REPO, "2500"): _product_pr(f"Evidence-Source: {self.SHA}")},
            compare={("dev", self.SHA): None, ("main", self.SHA): None},
        )
        assert _evaluate(fetcher).code == EXIT_PENDING


class TestBodyAndScopeVerdicts:
    def test_missing_evidence_source_is_pending(self) -> None:
        fetcher = FakeFetcher(prs={(PRODUCT_REPO, "2500"): _product_pr("no line yet")})
        verdict = _evaluate(fetcher)
        assert verdict.code == EXIT_PENDING
        assert "Evidence-Source" in verdict.reason

    def test_malformed_evidence_source_is_fail(self) -> None:
        fetcher = FakeFetcher(
            prs={(PRODUCT_REPO, "2500"): _product_pr("Evidence-Source: not-a-ref!")}
        )
        assert _evaluate(fetcher).code == EXIT_FAIL

    def test_dependency_bot_author_is_exempt(self) -> None:
        fetcher = FakeFetcher(
            prs={(PRODUCT_REPO, "2500"): _product_pr("", author="dependabot[bot]")}
        )
        verdict = _evaluate(fetcher)
        assert verdict.code == EXIT_PASS
        assert "dependency-bot" in verdict.reason

    def test_non_pr_event_is_not_applicable_pass(self) -> None:
        verdict = _evaluate(FakeFetcher(), event_name="push")
        assert verdict.code == EXIT_PASS
        assert "not applicable" in verdict.reason

    def test_unresolvable_pr_number_fails_closed(self) -> None:
        verdict = _evaluate(FakeFetcher(), pr_number="")
        assert verdict.code == EXIT_FAIL

    def test_product_pr_fetch_error_is_pending(self) -> None:
        fetcher = FakeFetcher(prs={(PRODUCT_REPO, "2500"): None})
        assert _evaluate(fetcher).code == EXIT_PENDING

    def test_evidence_source_override_skips_body_fetch(self) -> None:
        fetcher = FakeFetcher(
            prs={(OCC_REPO, "5032"): {"state": "MERGED", "mergeCommit": {"oid": "x"}}}
        )
        verdict = _evaluate(fetcher, evidence_source_override="OCC#5032")
        assert verdict.code == EXIT_PASS


class TestMainEntrypoint:
    def test_once_mode_returns_pending_exit_code(self, monkeypatch) -> None:
        # --once with an OPEN companion must surface PENDING (2), not PASS.
        import scripts.ci.check_occ_companion_merged as mod

        fetcher = FakeFetcher(
            prs={
                (PRODUCT_REPO, "77"): _product_pr("Evidence-Source: OCC#5032"),
                (OCC_REPO, "5032"): {"state": "OPEN", "mergeCommit": None},
            }
        )
        monkeypatch.setattr(mod, "GhFetcher", lambda: fetcher)
        rc = main(
            [
                "--once",
                "--repo",
                PRODUCT_REPO,
                "--pr-number",
                "77",
                "--occ-repo",
                OCC_REPO,
            ]
        )
        assert rc == EXIT_PENDING

    def test_deadline_converts_pending_to_fail(self, monkeypatch) -> None:
        import scripts.ci.check_occ_companion_merged as mod

        fetcher = FakeFetcher(
            prs={
                (PRODUCT_REPO, "77"): _product_pr("Evidence-Source: OCC#5032"),
                (OCC_REPO, "5032"): {"state": "OPEN", "mergeCommit": None},
            }
        )
        monkeypatch.setattr(mod, "GhFetcher", lambda: fetcher)
        rc = main(
            [
                "--repo",
                PRODUCT_REPO,
                "--pr-number",
                "77",
                "--occ-repo",
                OCC_REPO,
                "--deadline-seconds",
                "0",
                "--poll-interval-seconds",
                "0",
            ]
        )
        assert rc == EXIT_FAIL

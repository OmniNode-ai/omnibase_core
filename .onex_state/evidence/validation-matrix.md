# Cross-Repo Docs Validation Matrix

**Date:** 2026-04-29
**Feature:** Cross-repo docs validation gate and freshness sweep wiring
**Validator:** `uv run onex-validate-links --verbose` (per-repo) and cross-repo scan
**Executed from:** `$OMNI_HOME/omnibase_core` (owner of `onex-validate-links`)

---

## Phase A: Wave 2 Upstream PRs Verified

| PR | Repo | State | mergeCommit.oid |
|-----|------|-------|----------------|
| #31 | omnidash | MERGED | 7145e80c4663d9bb4435d191a0d5eaf9aa6945eb |
| #615 | omniintelligence | MERGED | 8bfd5037393eb5496748e2483719e5a5898fc2b0 |
| #296 | omnimemory | MERGED | f88186d2fabda5a5e33f9fe93a9efbd85403b122 |
| #529 | onex_change_control | MERGED | fa6ba81696b43843f9561c162b382c43fbbe7ca4 |
| #1464 | omniclaude | MERGED | 9fb64533285529384aa555c4cb7f0663e178b2ca |

All 5 Wave 2 tickets confirmed Done. All 5 PRs confirmed MERGED with non-null mergeCommit.oid.

---

## Per-Repo Freshness Matrix (10 in-scope repos)

### Legend
- OK = passes check
- GAP = documented gap / follow-up ticket filed
- N/A = not applicable (documented exemption)

| Repo | README exists | Links to docs index | docs/INDEX.md or docs/README.md | Commands verifiable | Referenced paths exist | Event-surface doc | validate-links result |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| omnibase_compat | OK | OK → docs/README.md | OK (docs/README.md) | OK | OK | N/A (no event bus) | PASS (1 gap: only in omni_worktrees, not main repo) |
| omnibase_core | OK | OK → docs/INDEX.md | OK (docs/INDEX.md) | OK | OK | N/A (kernel, no bus) | PASS after config fix |
| omnibase_infra | OK | OK → docs/INDEX.md | OK (docs/INDEX.md) | OK | GAP (anchor slugs) | OK (docs/architecture/EVENT_STREAMING_TOPICS.md) | FAIL — 53 broken anchors in new architecture docs (filed for follow-up) |
| omnibase_spi | OK | OK → docs/README.md | OK (docs/README.md) | OK | OK | N/A (protocol only) | PASS |
| omnimarket | OK | OK → docs/README.md | OK (docs/README.md) | OK | OK | N/A (marketplace) | PASS (2 gaps: only in omni_worktrees .venv paths) |
| omniintelligence | OK | OK → docs/INDEX.md | OK (docs/INDEX.md) | OK | GAP (3 broken cross-repo refs) | OK (docs/reference/EVENT_SURFACE.md) | FAIL — 3 broken links in src/ sub-READMEs (filed for follow-up) |
| omnimemory | OK | OK → docs/INDEX.md | OK (docs/INDEX.md) | OK | OK | N/A (storage layer) | PASS |
| onex_change_control | OK | GAP (links to docs/ dir only, no docs/INDEX.md) | GAP — no docs/INDEX.md or docs/README.md | OK | GAP (planning/IMPLEMENTATION_PLAN.md missing) | N/A | FAIL — 1 broken link (filed for follow-up) |
| omniclaude | OK | OK → docs/INDEX.md | OK (docs/INDEX.md) | OK | GAP (CONTRIBUTING.md ref, plugins/.venv paths) | N/A (thin wrapper) | FAIL — 25 broken links mostly in plugins/.venv (filed for follow-up) |
| omnidash | OK | GAP — no docs/INDEX.md or docs/README.md | GAP — no docs index | OK | OK | N/A (frontend) | N/A (npm repo, use npm run check) |

---

## Smoke Validation Results

| Repo | README → docs index (≤2 clicks) | Install/run/test commands | Owns/doesn't-own boundary | Dated plans as context only |
|------|:---:|:---:|:---:|:---:|
| omnibase_compat | OK (links to docs/README.md) | OK (uv add omnibase-compat) | OK | OK |
| omnibase_core | OK (links to docs/INDEX.md) | OK (uv sync && uv run pytest) | OK | OK |
| omnibase_infra | OK (links to docs/INDEX.md) | OK (uv sync && uv run pytest) | OK | OK |
| omnibase_spi | OK (links to docs/README.md) | OK (uv add omnibase-spi) | OK | OK |
| omnimarket | OK (links to docs/README.md) | OK (uv run pytest) | OK | OK |
| omniintelligence | OK (links to docs/INDEX.md) | OK | OK | OK |
| omnimemory | OK (links to docs/INDEX.md) | OK | OK | OK |
| onex_change_control | PARTIAL (links to docs/ dir) | OK | OK | OK |
| omniclaude | OK (links to docs/INDEX.md) | OK | OK | OK |
| omnidash | PARTIAL (no docs index) | OK (npm install && npm run dev) | OK | OK |

---

## Cross-Repo Validation Command

```bash
# Run from omnibase_core — it owns the onex-validate-links CLI
cd /path/to/omnibase_core  # or use $OMNI_HOME/omnibase_core
uv run onex-validate-links --verbose --cross-repo-root ${OMNI_HOME}
```

**Result with fix applied (omni_worktrees/** excluded):**
- omnibase_core: PASS (189 files, 1816 links, 0 broken)
- Cross-repo scan of omni_home root: 1 broken link before fix (pyright README in nested worktree .venv path) → 0 after fix

---

## CI Gate Status

`onex-validate-links` is already wired as a blocking CI gate in `omnibase_core/ci.yml`:
- Job: `docs-validation` (Phase 1, parallel with lint/pyright)
- Gate: Part of `quality-gate` which blocks `test-parallel`
- Reusable workflow: `validate-docs.yml` — callable by all repos

Repos not yet using the reusable workflow: omnibase_infra, omnibase_spi, omnimarket, omniintelligence, omnimemory, onex_change_control, omniclaude, omnidash. Follow-up tickets filed.

---

## Broken Links: Root Cause Analysis

### omnibase_infra (53 broken — all anchor slug mismatches)
New architecture docs (LLM_INFRASTRUCTURE.md, MCP_SERVICE_ARCHITECTURE.md, TOPIC_CATALOG_ARCHITECTURE.md, MCP_INTEGRATION_GUIDE.md, HANDLER_AUTHORING_GUIDE.md, ERROR_HANDLING_BEST_PRACTICES.md, REGISTRATION_WORKFLOW.md) have ToC links using `## HandlerMCP — Server Lifecycle` → anchor `#handlermcp-server-lifecycle` but GitHub converts em-dash to `--` (double-hyphen), so the actual anchor slug is `#handlermcp--server-lifecycle`. The validator correctly flags these. Filed for follow-up.

### omniintelligence (3 broken)
- `src/omniintelligence/tools/README.md:550` — `./C_API.md` does not exist (third-party file reference)
- `src/omniintelligence/tools/README.md:553` — reference-style link missing definition
- `src/omniintelligence/audit/README.md:835` — `/path/to/omni_home/tests/audit/io_audit_whitelist.yaml` absolute path (violates no-hardcoded-paths rule)
Filed for follow-up.

### onex_change_control (1 broken + docs index gap)
- `docs/VERSIONING_POLICY.md:96` — `planning/IMPLEMENTATION_PLAN.md` does not exist (was never created)
- No docs/INDEX.md or docs/README.md
Filed for follow-up.

### omniclaude (25 broken — mostly plugins/.venv paths)
- 22 in `plugins/onex/lib/.venv/` (onnxruntime, mdit_py_plugins, omniintelligence site-packages)
- 2 in a `omni_worktrees/omniclaude/.venv/` (worktree-scoped path)
- 1 genuine: `CONTRIBUTING.md` missing from root
Fix: add `plugins/**/.venv/**` to omniclaude's `.markdown-link-check.json` + add root CONTRIBUTING.md
Filed for follow-up.

### omnidash (no docs index)
omnidash README documents ADRs and CONTRIBUTING.md but has no `docs/INDEX.md` or `docs/README.md`. The docs/ directory contains plans/adr/audit but no canonical entrypoint. Filed for follow-up.

---

## Follow-up Work Filed

| Repo | Description |
|------|-------------|
| omnibase_infra | Fix 53 anchor slug mismatches in architecture docs (em-dash → double-hyphen) |
| omniintelligence | Fix 3 broken links in src/ sub-READMEs (C_API.md, missing ref, absolute path) |
| onex_change_control | Add docs/INDEX.md and fix VERSIONING_POLICY.md broken link |
| omniclaude | Add plugins/.venv to .markdown-link-check.json excludes, add CONTRIBUTING.md |
| omnidash | Add docs/INDEX.md as canonical docs entrypoint |
| all repos | Wire validate-docs.yml reusable workflow as required CI check in all 10 repos |

# Validation Ownership

**Owner:** `omnibase_core`
**Last verified:** 2026-04-24
**Verification:** `pyproject.toml`, validation scripts, OMN-9599 docs pass

This page defines which validation surfaces Core owns and how downstream repos
should consume them.

## Truth Boundary

`omnibase_core` owns reusable validation logic and CLI entrypoints for Core
architecture, docs links, topic naming, local path portability, contract checks,
and string-version guards.

Dated plans may describe validator migrations or cleanup sequences, but they are
not the validator source of truth unless promoted into stable docs. For example,
topic-cleanup execution plans are not current validator truth; the current topic
guard is the Core topic validator described here.

## CLI Entrypoints

Core publishes these validator entrypoints in `pyproject.toml`.

| Entrypoint | Owner | Purpose | Typical command |
|------------|-------|---------|-----------------|
| `onex-validate-links` | `omnibase_core` | Validate Markdown links and anchors. | `uv run onex-validate-links --verbose` |
| `onex-validate-topics` | `omnibase_core` | Validate topic constants against canonical ONEX topic format. | `uv run onex-validate-topics . --verbose` |
| `check-local-paths` | `omnibase_core` | Detect machine-specific absolute paths in text files. | `uv run check-local-paths docs src scripts` |
| `validate-string-versions` | `omnibase_core` | Detect string version literals that should use version models or constants. | `uv run validate-string-versions src` |
| `onex` | `omnibase_core` | Core CLI command group. | `uv run onex --help` |

## Markdown Link Validation

Use:

```bash
uv run onex-validate-links --verbose
```

For umbrella/cross-repo validation from a Core environment:

```bash
uv run onex-validate-links --verbose --cross-repo-root "$OMNI_HOME"
```

`$OMNI_HOME` should point to the local workspace root that contains sibling
repos. The validator scans Markdown files from the repo where it is invoked and
uses `--cross-repo-root` to resolve sibling-repo links.

Downstream repos should consume this as dev or CI tooling. They must not add
runtime imports or runtime dependencies on Core only for docs validation.

## Topic Validation

Use:

```bash
uv run onex-validate-topics . --verbose
```

The topic validator scans Python and TypeScript files that look topic-related
and validates `TOPIC_*` and `SUFFIX_*` constants against the canonical ONEX topic
format:

```text
onex.<kind>.<producer>.<event-name>.v<version>
```

It rejects flat legacy names and `{env}.`-prefixed topic strings. Documentation
examples should be marked as examples rather than presented as runtime
constants.

Current repo status is tracked in
[Topic Validation Status](../validation/TOPIC_VALIDATION_STATUS.md).

## Local Path Validation

Use:

```bash
uv run check-local-paths docs src scripts
```

This validator catches machine-specific absolute paths such as local user homes,
mounted volumes, and Windows user directories. Suppress only intentional examples
with `# local-path-ok`.

## Contract And Source Validators

Core also owns script-level validators under `scripts/` and
`scripts/validation/`, including:

- Contract fingerprinting and linting.
- Secret and hardcoded environment variable detection.
- Protocol export checks.
- Node purity checks.
- Transport import checks.
- Contract schema validation.
- Naming, typed-reference, import, and Pydantic-pattern validators.

See [scripts/README.md](../../scripts/README.md) and
[scripts/validation/README.md](../../scripts/validation/README.md) for command
details.

## Downstream Consumption

| Repo | Expected use |
|------|--------------|
| `omnibase_infra` | Docs links, topic naming, local path checks, contract/runtime boundary checks. |
| `omnibase_spi` | Docs links, protocol export validation patterns, local path checks. |
| `omnibase_compat` | CI/dev-only validation patterns where safe; no runtime Core dependency just for validation. |
| `omnimarket` | Docs links, topic/event-surface checks, local path checks. |
| `omniintelligence` | Topic/event-surface checks, docs links, local path checks. |
| `omnimemory` | Topic/event-surface checks, docs links, local path checks. |
| `onex_change_control` | Governance/freshness workflows consume Core validators as evidence producers. |
| `omniclaude` | Docs links and local path checks for plugin docs, prompts, and routing guidance. |
| `omnidash` and `omnidash-v2` | Docs links and topic/event-surface checks for dashboard-visible event contracts. |

## Validation Before Documentation Changes

For Core documentation-only changes:

```bash
uv run onex-validate-links --verbose
uv run check-local-paths README.md docs
```

For Core source or contract changes:

```bash
uv run pytest tests/ -q
uv run onex-validate-topics . --verbose
uv run check-local-paths docs src scripts
```

Record any validator gaps in the relevant pass note rather than weakening the
dependency boundary or promoting a dated plan as current truth.

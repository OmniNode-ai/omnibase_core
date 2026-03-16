# CI Documentation Validation Setup

How to add markdown link validation to an ONEX repository.

## Pre-commit Hook (repos with omnibase_core dependency)

Add to `.pre-commit-config.yaml` in a `- repo: local` block:

```yaml
- id: onex-validate-links
  name: Validate markdown links
  entry: uv run onex-validate-links --verbose
  language: system
  types: [markdown]
  pass_filenames: false
  stages: [pre-commit]
```

Repos with this hook: omnibase_core, omnibase_infra, omnibase_spi, omniclaude, omniintelligence, omnimemory, onex_change_control.

## CI via Reusable Workflow (all repos)

Add to your CI workflow:

```yaml
jobs:
  docs:
    uses: OmniNode-ai/omnibase_core/.github/workflows/validate-docs.yml@main
    with:
      check-external: true
```

For repos **without** omnibase_core as a dependency (omnidash, omninode_infra, omniweb, omnibase_compat):

```yaml
jobs:
  docs:
    uses: OmniNode-ai/omnibase_core/.github/workflows/validate-docs.yml@main
    with:
      check-external: true
      standalone: true
```

The `standalone: true` flag installs the validator via `uv tool install omnibase_core` instead of expecting it in the project dependencies.

## Configuration File

Create `.markdown-link-check.json` in the repository root:

```json
{
    "ignorePatterns": [
        {"pattern": "^https://linear\\.app"},
        {"pattern": "^https://github\\.com/OmniNode-ai"},
        {"pattern": "^http://localhost"},
        {"pattern": "^https://localhost"}
    ],
    "excludeFiles": [
        ".pytest_cache/**",
        ".venv/**",
        "venv/**",
        "node_modules/**",
        "archived/**"
    ],
    "checkExternal": false,
    "externalTimeout": 5000
}
```

Fields:
- `ignorePatterns`: Regex patterns for URLs to skip. Each entry is `{"pattern": "regex"}`.
- `excludeFiles`: Glob patterns for files to skip entirely.
- `checkExternal`: Whether to check HTTP/HTTPS links (overridden by `--check-external` CLI flag).
- `externalTimeout`: Timeout in milliseconds for external link checks.

## Cross-Repo Validation

To validate links that reference other repos (e.g., `omnibase_spi/docs/REGISTRY.md`):

```bash
uv run onex-validate-links --verbose --cross-repo-root /path/to/omni_home
```

## CLI Reference

```bash
uv run onex-validate-links                              # Validate all internal links
uv run onex-validate-links --verbose                    # Show all checked links
uv run onex-validate-links --check-external             # Also check HTTP/HTTPS links
uv run onex-validate-links docs/                        # Validate specific directory
uv run onex-validate-links --config path/to/config.json # Custom config file
uv run onex-validate-links --cross-repo-root /path      # Cross-repo link resolution
```

Exit codes: 0 = all valid, 1 = broken links, 2 = script error.

## Versioning

Callers use `@main` by default. If the reusable workflow interface changes incompatibly, a tagged release will be created (e.g., `@v1`) and all callers updated to pin to the tag.

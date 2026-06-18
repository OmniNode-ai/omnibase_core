# URL Contract Authority

**Status**: Active — OMN-12804 (part of OMN-12803 URL-authority epic)
**Schema version**: v1.0.0

---

## Design goal

Every URL or endpoint address used by ONEX services must resolve from a
contract YAML file — never from a string literal embedded in Python source,
and never from a bare `os.environ[*_URL]` read. This makes the complete set
of external dependencies auditable from a single location, and lets operator
overlays remap any endpoint without touching committed code.

---

## Two authority surfaces

ONEX separates URL authority into two complementary surfaces:

| Surface | Authority file | Owner | Scope |
|---------|---------------|-------|-------|
| **Model / inference routing** | `configs/bifrost_delegation.yaml` (omnimarket / omniclaude) | Bifrost router | LLM backend URLs, inference provider endpoints, per-model routing tiers |
| **Non-model integration endpoints** | `src/omnibase_core/contracts/integrations/catalog.yaml` (this repo) | Core platform | GitHub API, Linear GraphQL, OpenRouter non-inference, projection API, bus bootstrap, dashboard data sources, operator-specific endpoints |

Keeping these surfaces separate avoids conflation between *routing policy*
(model selection, tier escalation) and *address authority* (where a service
lives). Both surfaces are exempt from the url-authority gate — URLs inside
authority files are canonical, not violations.

---

## Catalog structure

`contracts/integrations/catalog.yaml` groups entries in three categories:

| Category | Meaning |
|----------|---------|
| `external_apis` | Public SaaS endpoints (GitHub, Linear, OpenRouter). Always have a canonical public default; operators override for GHES / air-gap. |
| `internal_infra` | Self-hosted endpoints (projection API, Redpanda, Infisical). No public default; `endpoint_url: null`. |
| `env_resolved` | Operator-only endpoints where no default exists and the operator always supplies the value. |

Each entry declares:

```yaml
- id: github.rest_api            # stable dotted identifier
  description: >
    Short prose used by the resolver and in diagnostics.
  endpoint_url: "https://api.github.com"   # null if always operator-supplied
  endpoint_url_env: ONEX_GITHUB_API_URL    # optional; overrides endpoint_url
```

---

## Resolution contract

Python code must never read a `*_URL` env var directly or embed an `https://`
literal. Instead it calls the catalog resolver:

```python
from omnibase_core.contracts.integrations.catalog_resolver import (
    IntegrationCatalogResolver,
)

resolver = IntegrationCatalogResolver.load()
url = resolver.endpoint("github.rest_api")
```

The resolver applies a site-specific overlay (env var
`ONEX_INTEGRATION_CATALOG_OVERLAY` or `~/.omninode/integration_overrides.yaml`)
at load time, so every deployment can remap endpoints without touching
committed YAML.

---

## Gate enforcement

`ValidatorUrlAuthority` (OMN-12818) enforces the "no URLs in source" rule as
a pre-commit hook (`check-url-authority`) and a required CI job
(`URL Authority Gate`) on every ONEX repo. Violations are detected in three
classes:

| Rule | Pattern |
|------|---------|
| `public-https-literal` | `"https://real.host.com/..."` in Python source |
| `env-url-read` | `os.environ["SOME_URL"]` / `os.environ.get("SOME_ENDPOINT")` |
| `url-const-assignment` | `BASE_URL = os.environ["FOO_URL"]` at module level |

**Ratchet behavior**: existing violations at gate activation are baselined by
content fingerprint. Only NEW fingerprints fail the gate. The baseline may
only shrink (burn-down); `assert_baseline_shrinks_only` guards against gaming.

**Suppression**: `# url-authority-ok: <concrete reason>` on a specific line
suppresses that line. For env reads that will be replaced by the catalog
resolver, use `# contract-config-ok:` until the migration lands.

---

## Adding a new integration

1. Add an entry to `catalog.yaml` under the correct category.
2. Set `endpoint_url` to the canonical value (or `null` if operator-only).
3. Add `endpoint_url_env` if operators can override it.
4. Update `catalog_resolver.py` to expose the new `id` via `endpoint()`.
5. In calling code, use `resolver.endpoint("your.new.id")` — zero literals.
6. Run `python -m omnibase_core.validation.validator_url_authority --all` to
   confirm no new literal snuck into source.
7. Cite the catalog entry id in the PR body.

---

## Migration debt

Existing violations are tracked by repo in burn-down tickets. The baseline
fingerprint files live at:

| Repo | Baseline file | Violation count at gate activation |
|------|--------------|-------------------------------------|
| `omnibase_core` | `src/omnibase_core/validation/baselines/url_authority_baseline.json` | 13 |
| `omnibase_infra` | `config/validation/url_authority_baseline.json` | 48 |

Burn-down tickets: OMN-12806 (omnibase_core), OMN-12807 (omnibase_infra),
OMN-12808 (other repos).

---

## Wiring (cross-repo pattern)

Each ONEX repo gets the `check-url-authority` pre-commit hook by pinning the
`omnibase_core` commit that includes the validator and adding the hook to the
repo's `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/OmniNode-ai/omnibase_core
  rev: <sha-of-omnibase_core-that-includes-validator>  # pragma: allowlist secret
  hooks:
    - id: check-stub-implementations
    - id: transport-mock-lint          # if the repo has that hook too
      args: [--baseline, config/validation/transport_mock_baseline.yaml]
    # OMN-12804: url-authority ratchet.  Existing violations frozen in
    # config/validation/url_authority_baseline.json.
    # New violations are blocked; burn-down tracked by OMN-12807.
    - id: check-url-authority
      args:
        - --repo
        - <repo-name>
        - --repo-root
        - .
        - --baseline
        - config/validation/url_authority_baseline.json
```

The CI gate (`.github/workflows/url-authority-gate.yml`) mirrors the
omnibase_core pattern:

```yaml
url-authority-gate:
  name: URL Authority Gate (OMN-12804)
  runs-on: [self-hosted, linux]
  steps:
    - uses: actions/checkout@v4
    - name: Run url-authority gate (full-repo, against frozen baseline)
      run: |
        python -m omnibase_core.validation.validator_url_authority \
          --all \
          --repo <repo-name> \
          --repo-root . \
          --baseline config/validation/url_authority_baseline.json
```

See OMN-13026 / PR #1962 in omnibase_infra for the reference pattern used to
wire transport-mock-lint; url-authority follows the same structure.

---

## See also

- `src/omnibase_core/validation/validator_url_authority.py` — gate implementation
- `src/omnibase_core/validation/baselines/url_authority_baseline.json` — core baseline
- `src/omnibase_core/contracts/integrations/catalog.yaml` — this authority catalog
- OMN-12803 — parent epic (all-URLs-from-contracts)
- OMN-12818 — gate implementation PR
- OMN-12806 / OMN-12807 / OMN-12808 — per-repo burn-down tickets

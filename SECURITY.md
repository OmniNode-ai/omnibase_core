# Security

## Supported Versions

Security fixes are handled on the latest maintained `omnibase_core` release
unless a release owner explicitly opens a backport branch.

## Reporting

Report suspected vulnerabilities privately to the repository maintainers. Do not
open a public issue for active vulnerabilities, leaked secrets, or exploit
details.

## Security-Relevant Boundaries

`omnibase_core` owns framework-level validation, contracts, node execution
patterns, and safe defaults. It does not own concrete secret stores,
infrastructure clients, runtime deployment, Kafka/Postgres operations, or host
registration. Those responsibilities belong in `omnibase_infra` or another
canonical implementation repo.

Do not add hardcoded secrets, local machine paths, or environment-specific
configuration to Core docs, examples, tests, or source.

## Required Local Checks

Run the relevant validators before changing security-sensitive code, docs, or
configuration:

```bash
uv run python scripts/validation/validate-secrets.py src/
uv run python scripts/validation/validate-hardcoded-env-vars.py src/
uv run check-local-paths docs src scripts
uv run onex-validate-links --verbose
```

For the broader validator map, see
[Validation Ownership](docs/reference/VALIDATION_OWNERSHIP.md).

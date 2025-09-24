# Repository Guidelines

## Project Structure & Module Organization
- `src/omnibase_core/`: core framework code (core, models, enums, exceptions, utils, validation).
- `tests/`: unit, integration, and performance suites (`tests/{unit,integration,performance}`; fixtures in `tests/fixtures`).
- `scripts/validation/`: ONEX validators used by pre-commit and CI.
- `docs/` and top-level *.md reports: design, standards, and performance notes.
- `examples/`: runnable examples and reference patterns.

## Build, Test, and Development Commands
- Setup: `poetry install` (Python 3.12). Optional hooks: `pre-commit install`.
- Lint/Format: `poetry run ruff check .`, `poetry run black .`, `poetry run isort .`.
- Type Check: `poetry run mypy --config-file mypy.ini`.
- Tests: `poetry run pytest -q` (async auto, test paths in `tests/`).
- Validators: `pre-commit run -a`. Key scripts: `validate_structure.py`, `validate_naming.py`, `validate-no-backward-compatibility.py`, `validate-contracts.py`, `validate-union-usage.py`, `validate-pydantic-patterns.py`, `validate-one-model-per-file.py`, `validate-typing-syntax.py`, `validate-enum-case-consistency.py`.
- Build: `poetry build`. CLI help (if installed): `poetry run omni-agent --help`.

## Coding Style & Naming Conventions
- Python: 4-space indent; Black line length 88; isort profile black; Ruff rules per `pyproject.toml`.
- Typing: strict MyPy; modern syntax (`X | Y`, `list[str]`); no `Dict[str, Any]` in models.
- Naming: one model per file; files `model_*.py` with classes `Model*`; enums `enum_*.py` with classes `Enum*` (validators enforce).
- Patterns to avoid: `to_dict/from_dict/*_legacy` methods, manual YAML parsing; rely on Pydantic and provided utilities.

## Testing Guidelines
- Framework: Pytest (+ pytest-asyncio). Test discovery matches `test_*.py` and `*_test.py`.
- Structure: unit in `tests/unit`, integration in `tests/integration`, performance in `tests/performance`.
- Coverage: target ≥85% where practical; include critical paths and error handling.
- Run full suite locally before PR: `pre-commit run -a && poetry run pytest`.

## Commit & Pull Request Guidelines
- Commits: Conventional style with clear scope; imperative mood; optional emoji accepted (see `git log`).
  - Examples: `feat(models): add ModelUserProfile`, `fix(validation): handle __pycache__`, `chore(ci): update hooks`.
- PRs: include description, linked issues, rationale, test results, and screenshots/logs when relevant. Require green pre-commit, passing tests, and ONEX validators.

## Security & Configuration Tips
- Never commit secrets; `.env` is ignored. Prefer Poetry extras (`--with full|cli|monitoring|kubernetes`).
- Use dependency injection and provided validators; do not introduce custom serialization or ad-hoc config loaders.

## Validation Suite Overview
- Pre-commit runs ONEX checks from `scripts/validation/`. Run individually, for example:
  - `poetry run python scripts/validation/validate_structure.py . omnibase_core`
  - `poetry run python scripts/validation/validate-no-backward-compatibility.py --dir src/`
  - `poetry run python scripts/validation/validate-contracts.py .`
- Key validators (one-liners):
  - `validate_structure.py`: Repository layout and required paths.
  - `validate_naming.py`: File/class naming (Model*/Enum*), casing.
  - `validate-no-backward-compatibility.py`: Blocks `to_dict/from_dict/*_legacy` patterns.
  - `validate-contracts.py`: Contract YAML schema and fields (e.g., `node_type`).
  - `validate-union-usage.py`: Safe Union usage and constraints.
  - `validate-pydantic-patterns.py`: Enforces approved Pydantic idioms.
  - `validate-one-model-per-file.py`: Exactly one model per file.
  - `validate-typing-syntax.py`: Modern typing (`|`, `list[str]`).
  - `validate-enum-case-consistency.py`: Consistent enum case and values.
- Address violations before PRs; pre-commit must be green.

- Additional hooks:
  - `validate-no-manual-yaml.py`: Ban ad-hoc YAML parse/dumps in code.
  - `validate-dict-any-usage.py`: Flag `Dict[str, Any]` in typed domains.
  - `validate-no-dict-conversion.py` / `validate-no-dict-methods.py`: Disallow dict conversions and `to_dict/from_dict`.
  - `validate-string-versions-and-ids.py`: Enforce version/id string patterns.
  - `audit_optional.py`: Audit Optional usage and nullability.
  - `validate-generic-patterns.py` / `validate-generic-type-methods.py`: Enforce safe generics and forbid type-bound methods.
  - `validate-typed-references.py`: Detect typed-reference anti-patterns.
  - `validate-timestamp-fields.py`: Ensure timestamp fields use approved types.
  - `validate-onex-error-compliance.py`: Standardize ONEX error models/handling.
  - `validate-stubbed-functionality.py`: Block stubbed/placeholder implementations.
  - `validate-elif-limit.py`: Enforce max elif chain length.

## Further Reading
- `docs/VALIDATION_INTEGRATION_GUIDE.md`: How validators integrate with pre-commit and CI.
- `STANDARDS_COMPLIANCE.md`: ONEX standards applied in this repo.
- `OMNI_ECOSYSTEM_STANDARDIZATION_FRAMEWORK.md`: Ecosystem-wide conventions and rationale.

## Shared Agent References
- Local knowledge base (for contributors using the agent toolchain):
  - `~/.claude/agents/AGENT_FRAMEWORK.md` (agent architecture)
  - `~/.claude/agents/agent-testing.md` (testing standards)
  - `~/.claude/agents/agent-code-quality.md` (quality gates)
  - `~/.claude/agents/agent-commit.md` and `~/.claude/agents/agent-pr-manager.md` (commit/PR workflow)
  - `~/.claude/CORE_PRINCIPLES.md` and `~/.claude/agents/ONEX_4_Node_System_Developer_Guide.md`
- Example to open: `open ~/.claude/agents/agent-testing.md` (macOS) or `xdg-open` on Linux.
